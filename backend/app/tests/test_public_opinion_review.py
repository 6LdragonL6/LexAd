from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.engine.industry import format_industries, split_industries
from app.engine.public_opinion import run_public_opinion_review
from app.models.knowledge import (
    PublicOpinionEvent,
    PublicOpinionEventStatus,
    PublicOpinionEventVersion,
    PublicOpinionLibraryVersion,
    ReviewModuleStatus,
)
from app.models.material import Material, MaterialStatus
from app.models.review import Review
from app.models.user import User, UserRole
from app.schemas.review import EngineResult, LayerResult
from app.services import review_service
from app.services.public_opinion_case_service import sync_case_file


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _seed_user(db):
    user = User(
        id="admin-1",
        username="admin-test",
        password="not-used",
        display_name="管理员",
        role=UserRole.admin,
        dept_name="管理部",
    )
    db.add(user)
    return user


def _seed_public_opinion_case(db, user_id: str):
    event = PublicOpinionEvent(
        id="po-event-1",
        title="消费者尊重争议",
        source_text="广告表达被认为不尊重消费者，引发截图传播。",
        consequence_text="品牌声誉受损。",
        status=PublicOpinionEventStatus.published,
        created_by_id=user_id,
        published_by_id=user_id,
        published_at=datetime.now(timezone.utc),
    )
    version = PublicOpinionEventVersion(
        id="po-version-1",
        event_id=event.id,
        version=1,
        title=event.title,
        industry=["食品"],
        platforms=["抖音"],
        source_text=event.source_text,
        event_process={"trigger": "不尊重消费者", "timeline": [], "brand_response": "", "outcome": "品牌声誉受损"},
        consequences={"reputation": "负面评论增加", "business": "", "regulatory": ""},
        risk_topics=["消费者尊重"],
        trigger_patterns=["不尊重消费者"],
        affected_groups=["消费者"],
        propagation_drivers=["截图传播"],
        normalized_tags={"topic": "consumer-respect"},
        severity_level="high",
        summary="消费者尊重争议",
        confidence=80,
    )
    library = PublicOpinionLibraryVersion(
        id="po-lib-1",
        version=1,
        event_ids=[event.id],
        event_count=1,
        created_by_id=user_id,
    )
    db.add_all([event, version, library])
    return event


def test_public_opinion_empty_library_does_not_return_low_risk(monkeypatch):
    import app.engine.public_opinion as public_opinion_engine

    monkeypatch.setattr(
        public_opinion_engine.model_service,
        "explain_public_opinion_risk",
        lambda **_kwargs: (_ for _ in ()).throw(public_opinion_engine.model_service.ModelServiceError("no api key")),
    )
    factory = _session_factory()
    db = factory()
    try:
        result = run_public_opinion_review(
            material_text="普通广告文案",
            industry="食品",
            platforms=["抖音"],
            db=db,
        )
        assert result.status == "succeeded"
        assert result.result["status"] == "uncertain"
        assert result.result["risk_level"] == "uncertain"
        assert result.result["knowledge_base_available"] is False
    finally:
        db.close()


def test_public_opinion_review_hits_published_case_with_model_fallback(monkeypatch):
    factory = _session_factory()
    db = factory()
    user = _seed_user(db)
    _seed_public_opinion_case(db, user.id)
    db.commit()

    def fail_model(**_kwargs):
        from app.services.model_service import ModelServiceError

        raise ModelServiceError("no api key")

    import app.engine.public_opinion as public_opinion_engine

    monkeypatch.setattr(public_opinion_engine.model_service, "explain_public_opinion_risk", fail_model)
    try:
        result = run_public_opinion_review(
            material_text="这句文案可能被认为不尊重消费者，请谨慎。",
            industry="食品",
            platforms=["抖音"],
            db=db,
        )
        assert result.status == "succeeded"
        assert result.library_version_id == "po-lib-1"
        assert result.result["risk_level"] == "high"
        assert result.result["model_available"] is False
        assert result.result["similar_events"][0]["event_id"] == "po-event-1"
    finally:
        db.close()


def test_split_industries_supports_compatible_joined_string():
    assert split_industries("食品、直播电商，金融/食品") == ["食品", "直播电商", "金融"]
    assert format_industries(["食品", "直播电商", "食品"]) == "食品、直播电商"


def test_public_opinion_review_does_not_show_context_only_case(monkeypatch):
    factory = _session_factory()
    db = factory()
    user = _seed_user(db)
    _seed_public_opinion_case(db, user.id)
    db.commit()

    def fail_model(**_kwargs):
        from app.services.model_service import ModelServiceError

        raise ModelServiceError("no api key")

    import app.engine.public_opinion as public_opinion_engine

    monkeypatch.setattr(public_opinion_engine.model_service, "explain_public_opinion_risk", fail_model)
    try:
        result = run_public_opinion_review(
            material_text="普通广告文案，没有直接触发词。",
            industry="金融、食品",
            platforms=[],
            db=db,
        )
        assert result.status == "succeeded"
        assert result.result["deterministic_hits"] == []
        assert result.result["similar_events"] == []
        assert result.result["risk_level"] == "uncertain"
    finally:
        db.close()


def test_real_cases_flag_suffering_marketing_and_recall_taoli_when_model_is_down(monkeypatch):
    factory = _session_factory()
    db = factory()
    user = _seed_user(db)
    db.commit()
    sync_case_file(db, user)
    db.commit()

    import app.engine.public_opinion as public_opinion_engine

    monkeypatch.setattr(
        public_opinion_engine.model_service,
        "explain_public_opinion_risk",
        lambda **_kwargs: (_ for _ in ()).throw(public_opinion_engine.model_service.ModelServiceError("model down")),
    )
    try:
        result = run_public_opinion_review(
            material_text="被生活毒打过，才懂这盒月饼的甜。成年人的世界没有容易二字，咬咬牙，把苦咽下去，把甜留给自己。",
            industry="食品",
            platforms=["电梯广告"],
            db=db,
        )
        assert result.result["risk_level"] in {"medium", "high", "severe"}
        assert "价值观争议" in result.result["risk_topics"]
        assert "苦难营销" in result.result["risk_topics"]
        assert any("桃李面包" in item["title"] for item in result.result["similar_events"])
        assert result.result["assessment_source"] == "local"
    finally:
        db.close()


def test_ai_can_find_new_risk_without_local_cases(monkeypatch):
    factory = _session_factory()
    db = factory()
    import app.engine.public_opinion as public_opinion_engine

    monkeypatch.setattr(
        public_opinion_engine.model_service,
        "explain_public_opinion_risk",
        lambda **_kwargs: {
            "risk_level": "high",
            "risk_score": 68,
            "risk_topics": ["焦虑营销"],
            "affected_groups": ["职场人"],
            "propagation_drivers": ["情绪共鸣"],
            "evidence_quotes": ["三十岁还没成功就是失败"],
            "counter_signals": [],
            "suggestions": ["删除年龄焦虑表达"],
            "explanation": "将年龄与失败强绑定。",
            "confidence": 90,
            "matched_case_ids": [],
        },
    )
    try:
        result = run_public_opinion_review(
            material_text="三十岁还没成功就是失败，现在下单改变命运。",
            industry="通用",
            platforms=[],
            db=db,
        )
        assert result.result["risk_level"] == "high"
        assert result.result["assessment_source"] == "ai"
        assert result.result["knowledge_base_available"] is False
        assert "焦虑营销" in result.result["risk_topics"]
    finally:
        db.close()


def test_single_trigger_in_game_context_does_not_recall_taoli(monkeypatch):
    factory = _session_factory()
    db = factory()
    user = _seed_user(db)
    db.commit()
    sync_case_file(db, user)
    db.commit()
    import app.engine.public_opinion as public_opinion_engine

    monkeypatch.setattr(
        public_opinion_engine.model_service,
        "explain_public_opinion_risk",
        lambda **_kwargs: (_ for _ in ()).throw(public_opinion_engine.model_service.ModelServiceError("model down")),
    )
    try:
        result = run_public_opinion_review(
            material_text="今晚排位被对面毒打，继续练技术明天再战。",
            industry="游戏",
            platforms=[],
            db=db,
        )
        assert result.result["risk_level"] in {"low", "uncertain"}
        assert not any("桃李面包" in item["title"] for item in result.result["similar_events"])
    finally:
        db.close()


def test_high_confidence_local_ai_disagreement_requires_manual_review(monkeypatch):
    factory = _session_factory()
    db = factory()
    user = _seed_user(db)
    _seed_public_opinion_case(db, user.id)
    db.commit()
    import app.engine.public_opinion as public_opinion_engine

    monkeypatch.setattr(
        public_opinion_engine.model_service,
        "explain_public_opinion_risk",
        lambda **_kwargs: {
            "risk_level": "low",
            "risk_score": 10,
            "risk_topics": [],
            "affected_groups": [],
            "propagation_drivers": [],
            "evidence_quotes": ["不尊重消费者"],
            "counter_signals": ["模型认为语境温和"],
            "suggestions": [],
            "explanation": "模型判断风险较低。",
            "confidence": 95,
            "matched_case_ids": [],
        },
    )
    try:
        result = run_public_opinion_review(
            material_text="这句文案不尊重消费者",
            industry="食品",
            platforms=["抖音"],
            db=db,
        )
        assert result.result["risk_level"] == "high"
        assert result.result["requires_manual_review"] is True
        assert result.result["disagreement_reason"]
    finally:
        db.close()


def test_review_task_aggregates_legal_and_public_opinion(monkeypatch):
    factory = _session_factory()
    db = factory()
    user = _seed_user(db)
    _seed_public_opinion_case(db, user.id)
    material = Material(
        id="material-1",
        name="测试物料",
        raw_text="这句广告可能不尊重消费者",
        industry="食品",
        platforms=["抖音"],
        submitter_id=user.id,
    )
    db.add(material)
    db.commit()
    db.close()

    monkeypatch.setattr(review_service, "SessionLocal", factory)

    def fake_pipeline(_text, _industry, _platforms, _db):
        return EngineResult(
            risk_score=92,
            layer1=LayerResult(layer="硬规则"),
            layer2=LayerResult(layer="语义"),
            layer3=LayerResult(layer="证明材料"),
            layer4=LayerResult(layer="平台"),
            summary="法律低风险",
        )

    def fake_explain(**_kwargs):
        return {
            "risk_level": "high",
            "risk_topics": ["消费者尊重"],
            "affected_groups": ["消费者"],
            "propagation_drivers": ["截图传播"],
            "suggestions": ["品牌负责人复核"],
            "explanation": "存在舆情触发点",
            "confidence": 88,
        }

    monkeypatch.setattr(review_service, "run_review_pipeline", fake_pipeline)
    import app.engine.public_opinion as public_opinion_engine

    monkeypatch.setattr(public_opinion_engine.model_service, "explain_public_opinion_risk", fake_explain)

    db = factory()
    review, _ = review_service.create_ai_review(db, "material-1")
    db.close()

    review_service.execute_ai_review(review.id)

    db = factory()
    try:
        stored = db.query(Review).filter(Review.id == review.id).one()
        material = db.query(Material).filter(Material.id == "material-1").one()
        assert stored.task_status == "completed"
        assert stored.legal_module_status == ReviewModuleStatus.succeeded
        assert stored.public_opinion_module_status == ReviewModuleStatus.succeeded
        assert stored.public_opinion_library_version_id == "po-lib-1"
        assert stored.public_opinion_result["risk_level"] == "high"
        assert stored.public_opinion_result["model_available"] is True
        assert material.status == MaterialStatus.pending_legal
    finally:
        db.close()


def test_review_task_keeps_legal_result_when_public_opinion_fails(monkeypatch):
    factory = _session_factory()
    db = factory()
    user = _seed_user(db)
    material = Material(
        id="material-1",
        name="测试物料",
        raw_text="普通广告",
        industry="食品",
        platforms=[],
        submitter_id=user.id,
    )
    db.add(material)
    db.commit()
    db.close()

    monkeypatch.setattr(review_service, "SessionLocal", factory)
    monkeypatch.setattr(
        review_service,
        "run_review_pipeline",
        lambda *_args: EngineResult(risk_score=90, summary="法律完成"),
    )

    def fail_public_opinion(**_kwargs):
        raise RuntimeError("public opinion engine down")

    monkeypatch.setattr(review_service, "run_public_opinion_review", fail_public_opinion)

    db = factory()
    review, _ = review_service.create_ai_review(db, "material-1")
    db.close()
    review_service.execute_ai_review(review.id)

    db = factory()
    try:
        stored = db.query(Review).filter(Review.id == review.id).one()
        material = db.query(Material).filter(Material.id == "material-1").one()
        assert stored.task_status == "completed"
        assert stored.legal_module_status == ReviewModuleStatus.succeeded
        assert stored.public_opinion_module_status == ReviewModuleStatus.failed
        assert "public opinion engine down" in stored.public_opinion_module_error
        assert material.status == MaterialStatus.pending_legal
    finally:
        db.close()
