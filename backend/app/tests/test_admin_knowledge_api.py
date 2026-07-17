"""Admin knowledge center API tests for v0.4.2."""

import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.knowledge import PublicOpinionEvent, PublicOpinionEventVersion
from app.models.user import User, UserRole
from app.services import admin_knowledge_service
from app.services.public_opinion_case_service import BUILTIN_CASES_PATH
from app.core.config import get_settings


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _user(user_id: str, role: UserRole) -> User:
    return User(
        id=user_id,
        username=f"user-{user_id}",
        password="not-used",
        display_name="Test User",
        role=role,
        dept_name="Test",
    )


def _client(role: UserRole = UserRole.admin) -> tuple[TestClient, sessionmaker]:
    factory = _session_factory()
    db = factory()
    user = _user(f"{role.value}-1", role)
    db.add(user)
    db.commit()
    db.close()

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return TestClient(app), factory


def _clear_overrides():
    app.dependency_overrides.clear()


def test_admin_required_for_knowledge_center():
    client, _ = _client(UserRole.marketing)
    try:
        response = client.get("/api/v1/admin/knowledge/public-opinion/events")
        assert response.status_code == 403
        assert client.get("/api/v1/admin/settings/ai").status_code == 403
        assert client.get("/api/v1/admin/settings/recycle-bin").status_code == 403
    finally:
        _clear_overrides()


def test_competition_mode_makes_admin_knowledge_and_ai_settings_read_only():
    client, _ = _client(UserRole.admin)
    settings = get_settings()
    original_mode = settings.COMPETITION_MODE
    settings.COMPETITION_MODE = True
    try:
        listed = client.get("/api/v1/admin/knowledge/public-opinion/events")
        assert listed.status_code == 200

        create_blocked = client.post(
            "/api/v1/admin/knowledge/public-opinion/events",
            json={
                "external_id": "blocked-case",
                "title": "不应创建",
                "source_text": "竞赛保护模式测试",
                "consequence_text": "无",
                "source_meta": {},
            },
        )
        assert create_blocked.status_code == 403
        assert create_blocked.json()["code"] == "competition_mode_read_only"

        ai_settings_blocked = client.put(
            "/api/v1/admin/settings/ai",
            json={"api_key": "unit-test-key-should-not-be-saved"},
        )
        assert ai_settings_blocked.status_code == 403
        assert ai_settings_blocked.json()["code"] == "competition_mode_read_only"

        recycle_bin_blocked = client.post(
            "/api/v1/admin/settings/recycle-bin",
            json={
                "target_type": "material",
                "target_id": "protected-material",
                "display_name": "不应创建",
                "snapshot": {},
            },
        )
        assert recycle_bin_blocked.status_code == 403
        assert recycle_bin_blocked.json()["code"] == "competition_mode_read_only"
    finally:
        settings.COMPETITION_MODE = original_mode
        _clear_overrides()


def test_public_opinion_event_lifecycle_and_audit_logs():
    client, _ = _client(UserRole.admin)
    try:
        created = client.post(
            "/api/v1/admin/knowledge/public-opinion/events",
            json={
                "external_id": "case-001",
                "title": "争议广告事件",
                "source_text": "广告文案引发消费者争议。",
                "consequence_text": "品牌声誉受损。",
                "source_meta": {"source": "internal"},
            },
        )
        assert created.status_code == 201
        event_id = created.json()["id"]
        assert created.json()["status"] == "draft"

        structured = client.post(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}/structure")
        assert structured.status_code == 202
        assert structured.json()["event_id"] == event_id

        published = client.post(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}/publish")
        assert published.status_code == 200
        assert published.json()["status"] == "published"

        archived = client.post(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}/archive")
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"

        restored = client.post(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}/restore")
        assert restored.status_code == 200
        assert restored.json()["status"] == "published"

        detail = client.get(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}")
        assert detail.status_code == 200
        assert len(detail.json()["versions"]) == 1

        deleted = client.delete(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}").status_code == 404

        recycle_bin = client.get("/api/v1/admin/settings/recycle-bin?target_type=public_opinion_event")
        assert recycle_bin.status_code == 200
        assert recycle_bin.json()["items"][0]["target_id"] == event_id

        logs = client.get("/api/v1/admin/knowledge/audit-logs?target_type=public_opinion_event")
        assert logs.status_code == 200
        actions = [item["action"] for item in logs.json()]
        assert "public_opinion.publish" in actions
        assert "public_opinion.archive" in actions
        assert "public_opinion.restore" in actions
        assert "recycle_bin.delete" in actions
    finally:
        _clear_overrides()


def test_platform_rule_version_activation_and_rollback():
    client, _ = _client(UserRole.admin)
    try:
        rule_set = client.post(
            "/api/v1/admin/knowledge/platform-rules",
            json={
                "platform_name": "douyin",
                "display_name": "抖音",
                "description": "短视频平台规则",
            },
        )
        assert rule_set.status_code == 201
        rule_set_id = rule_set.json()["id"]

        first = client.post(
            f"/api/v1/admin/knowledge/platform-rules/{rule_set_id}/versions",
            json={
                "version_label": "2026-07-A",
                "raw_text": "不得使用绝对化用语",
                "structured_rules": [{"rule_id": "r1", "text": "不得使用最好"}],
            },
        )
        assert first.status_code == 201
        first_id = first.json()["id"]

        activated_first = client.post(f"/api/v1/admin/knowledge/platform-rule-versions/{first_id}/activate")
        assert activated_first.status_code == 200
        assert activated_first.json()["status"] == "active"

        second = client.post(
            f"/api/v1/admin/knowledge/platform-rules/{rule_set_id}/versions",
            json={
                "version_label": "2026-07-B",
                "raw_text": "不得使用绝对化用语；不得虚构效果",
                "structured_rules": [
                    {"rule_id": "r1", "text": "不得使用最好"},
                    {"rule_id": "r2", "text": "不得虚构效果"},
                ],
            },
        )
        assert second.status_code == 201
        second_id = second.json()["id"]
        assert second.json()["diff_summary"]["added_count"] == 1

        activated_second = client.post(f"/api/v1/admin/knowledge/platform-rule-versions/{second_id}/activate")
        assert activated_second.status_code == 200
        assert activated_second.json()["status"] == "active"

        rolled_back = client.post(f"/api/v1/admin/knowledge/platform-rule-versions/{first_id}/rollback")
        assert rolled_back.status_code == 200
        assert rolled_back.json()["status"] == "active"

        detail = client.get(f"/api/v1/admin/knowledge/platform-rules/{rule_set_id}")
        assert detail.status_code == 200
        assert detail.json()["active_version"]["id"] == first_id

        logs = client.get("/api/v1/admin/knowledge/audit-logs?target_type=platform_rule_version")
        assert logs.status_code == 200
        actions = [item["action"] for item in logs.json()]
        assert "platform_rule_version.activate" in actions
        assert "platform_rule_version.rollback" in actions
    finally:
        _clear_overrides()


def test_public_opinion_import_template_is_available_to_admin():
    client, _ = _client(UserRole.admin)
    try:
        response = client.get("/api/v1/admin/knowledge/public-opinion/import-template")
        assert response.status_code == 200
        data = response.json()
        assert data["schema_version"] == "1.0"
        assert isinstance(data["events"], list)
        assert data["events"][0]["event_process"]["trigger"]
    finally:
        _clear_overrides()


def test_public_opinion_import_preview_and_confirm_creates_drafts():
    client, factory = _client(UserRole.admin)
    payload = {
        "schema_version": "1.0",
        "events": [
            {
                "external_id": "case-import-001",
                "title": "导入事件",
                "source_text": "某广告表达引发讨论。",
                "event_process": {
                    "trigger": "广告表达被认为不尊重消费者",
                    "timeline": [],
                    "brand_response": "",
                    "outcome": "品牌公开道歉",
                },
                "consequences": {"reputation": "负面评论增加"},
            },
            {
                "external_id": "case-import-bad",
                "title": "",
                "source_text": "",
                "event_process": {"trigger": "", "outcome": ""},
            },
        ],
    }
    try:
        preview = client.post(
            "/api/v1/admin/knowledge/public-opinion/import/preview",
            json={"payload": payload, "file_name": "cases.json"},
        )
        assert preview.status_code == 201
        job = preview.json()
        assert job["status"] == "validation_failed"
        assert job["total_items"] == 2
        assert job["valid_items"] == 1
        assert job["invalid_items"] == 1

        db = factory()
        try:
            assert db.query(PublicOpinionEvent).count() == 0
        finally:
            db.close()

        confirmed = client.post(f"/api/v1/admin/knowledge/public-opinion/imports/{job['id']}/confirm", json={})
        assert confirmed.status_code == 200
        result = confirmed.json()
        assert result["job"]["status"] == "completed"
        assert len(result["created_event_ids"]) == 1

        events = client.get("/api/v1/admin/knowledge/public-opinion/events").json()
        assert events["total"] == 1
        assert events["items"][0]["external_id"] == "case-import-001"
        assert events["items"][0]["status"] == "draft"
    finally:
        _clear_overrides()


def test_public_opinion_import_accepts_real_team_case_schema_and_merges_duplicates():
    client, factory = _client(UserRole.admin)
    payload = json.loads(BUILTIN_CASES_PATH.read_text(encoding="utf-8"))
    try:
        preview = client.post(
            "/api/v1/admin/knowledge/public-opinion/import/preview",
            json={"payload": payload, "file_name": "sentiment_cases.json"},
        )
        assert preview.status_code == 201
        job = preview.json()
        assert job["status"] == "validated"
        assert job["total_items"] == 34
        assert job["valid_items"] == 33
        assert job["invalid_items"] == 0

        confirmed = client.post(
            f"/api/v1/admin/knowledge/public-opinion/imports/{job['id']}/confirm",
            json={},
        )
        assert confirmed.status_code == 200
        assert len(confirmed.json()["created_event_ids"]) == 33
        db = factory()
        try:
            assert db.query(PublicOpinionEvent).count() == 33
            assert db.query(PublicOpinionEventVersion).count() == 33
            assert db.query(PublicOpinionEvent).filter_by(external_id="sent-case-018").count() == 1
            assert db.query(PublicOpinionEvent).filter_by(external_id="sent-case-033").count() == 0
        finally:
            db.close()
    finally:
        _clear_overrides()


def test_public_opinion_import_duplicate_external_id_can_skip():
    client, _ = _client(UserRole.admin)
    payload = {
        "schema_version": "1.0",
        "events": [
            {
                "external_id": "case-dup",
                "title": "重复事件",
                "source_text": "事件内容。",
                "event_process": {
                    "trigger": "触发点",
                    "outcome": "已有后果",
                },
            }
        ],
    }
    try:
        first_preview = client.post(
            "/api/v1/admin/knowledge/public-opinion/import/preview",
            json={"payload": payload, "file_name": "first.json"},
        )
        assert first_preview.status_code == 201
        first_confirm = client.post(
            f"/api/v1/admin/knowledge/public-opinion/imports/{first_preview.json()['id']}/confirm",
            json={},
        )
        assert first_confirm.status_code == 200

        duplicate_preview = client.post(
            "/api/v1/admin/knowledge/public-opinion/import/preview",
            json={"payload": payload, "file_name": "second.json"},
        )
        assert duplicate_preview.status_code == 201
        duplicate_job = duplicate_preview.json()
        assert duplicate_job["error_summary"]["duplicate_external_ids"] == ["case-dup"]

        duplicate_confirm = client.post(
            f"/api/v1/admin/knowledge/public-opinion/imports/{duplicate_job['id']}/confirm",
            json={"duplicate_actions": {"case-dup": "skip"}},
        )
        assert duplicate_confirm.status_code == 200
        assert duplicate_confirm.json()["skipped_external_ids"] == ["case-dup"]

        events = client.get("/api/v1/admin/knowledge/public-opinion/events").json()
        assert events["total"] == 1
    finally:
        _clear_overrides()


def test_public_opinion_structure_uses_shared_model_service(monkeypatch):
    client, _ = _client(UserRole.admin)

    def fake_structure_public_opinion_case(**_kwargs):
        return {
            "industry": ["食品"],
            "platforms": ["微博"],
            "event_process": {
                "trigger": "敏感表达",
                "timeline": [],
                "brand_response": "",
                "outcome": "出现负面评论",
            },
            "consequences": {
                "reputation": "声誉受损",
                "business": "",
                "regulatory": "",
                "duration_days": None,
                "severity_hint": "medium",
            },
            "risk_topics": ["消费者尊重"],
            "trigger_patterns": ["不尊重消费者"],
            "affected_groups": ["消费者"],
            "propagation_drivers": ["截图传播"],
            "normalized_tags": {"severity": "medium"},
            "severity_level": "medium",
            "summary": "模型整理摘要",
            "confidence": 82,
        }

    monkeypatch.setattr(
        admin_knowledge_service.model_service,
        "structure_public_opinion_case",
        fake_structure_public_opinion_case,
    )
    try:
        created = client.post(
            "/api/v1/admin/knowledge/public-opinion/events",
            json={
                "title": "模型整理事件",
                "source_text": "广告内容被消费者批评。",
                "consequence_text": "出现负面评论。",
            },
        )
        assert created.status_code == 201
        event_id = created.json()["id"]

        structured = client.post(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}/structure")
        assert structured.status_code == 202
        data = structured.json()
        assert data["model_name"] == "deepseek"
        assert data["summary"] == "模型整理摘要"
        assert data["confidence"] == 82
        assert data["risk_topics"] == ["消费者尊重"]
    finally:
        _clear_overrides()
