"""Admin knowledge center API tests for v0.4.2."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


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
    finally:
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

        cannot_delete = client.delete(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}")
        assert cannot_delete.status_code == 400

        archived = client.post(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}/archive")
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"

        restored = client.post(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}/restore")
        assert restored.status_code == 200
        assert restored.json()["status"] == "published"

        detail = client.get(f"/api/v1/admin/knowledge/public-opinion/events/{event_id}")
        assert detail.status_code == 200
        assert len(detail.json()["versions"]) == 1

        logs = client.get("/api/v1/admin/knowledge/audit-logs?target_type=public_opinion_event")
        assert logs.status_code == 200
        actions = [item["action"] for item in logs.json()]
        assert "public_opinion.publish" in actions
        assert "public_opinion.archive" in actions
        assert "public_opinion.restore" in actions
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
