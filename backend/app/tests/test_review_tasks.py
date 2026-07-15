"""Background review task state regression tests."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from datetime import datetime, timedelta, timezone

from app.db.base import Base
from app.models.material import Material, MaterialStatus, MaterialSubmissionSnapshot
from app.models.review import Review
from app.models.user import User, UserRole
from app.schemas.review import EngineResult
from app.engine.public_opinion import PublicOpinionReview
from app.services import review_service


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _seed(factory):
    db = factory()
    user = User(
        id="user-1",
        username="market-test",
        password="not-used",
        display_name="市场测试",
        role=UserRole.marketing,
        dept_name="市场部",
    )
    material = Material(
        id="material-1",
        name="测试物料",
        raw_text="普通广告文案",
        industry="食品",
        platforms=[],
        submitter_id=user.id,
    )
    db.add_all([user, material])
    db.commit()
    db.close()


def test_background_review_completes_and_prevents_duplicate(monkeypatch):
    factory = _session_factory()
    _seed(factory)
    monkeypatch.setattr(review_service, "SessionLocal", factory)
    seen: dict[str, str] = {}

    def fake_pipeline(text, industry, platforms, _db):
        seen["legal_text"] = text
        return EngineResult(compliance_score=95, summary="测试完成")

    def fake_public_opinion(**kwargs):
        seen["public_opinion_text"] = kwargs["material_text"]
        return PublicOpinionReview(status="completed", result={"risk_level": "low"}, safety_score=90)

    monkeypatch.setattr(review_service, "run_review_pipeline", fake_pipeline)
    monkeypatch.setattr(review_service, "run_public_opinion_review", fake_public_opinion)

    db = factory()
    review, created = review_service.create_ai_review(db, "material-1")
    duplicate, duplicate_created = review_service.create_ai_review(db, "material-1")
    assert created is True
    assert duplicate_created is False
    assert duplicate.id == review.id
    review_id = review.id
    snapshot = db.query(MaterialSubmissionSnapshot).filter(MaterialSubmissionSnapshot.id == review.submission_snapshot_id).one()
    assert snapshot.raw_text == "普通广告文案"
    material = db.query(Material).filter(Material.id == "material-1").one()
    material.raw_text = "修改后的工作副本"
    db.commit()
    assert snapshot.raw_text == "普通广告文案"
    db.close()

    review_service.execute_ai_review(review_id)

    db = factory()
    stored = db.query(Review).filter(Review.id == review_id).one()
    material = db.query(Material).filter(Material.id == "material-1").one()
    assert stored.task_status == "completed"
    assert stored.legal_compliance_score == 95
    assert stored.public_opinion_safety_score == 90
    assert seen == {"legal_text": "普通广告文案", "public_opinion_text": "普通广告文案"}
    assert material.status == MaterialStatus.pending_legal
    legal = User(
        id="legal-1",
        username="legal-test",
        password="not-used",
        display_name="法务测试",
        role=UserRole.legal,
        dept_name="法务部",
    )
    db.add(legal)
    db.commit()
    queue = review_service.get_legal_queue(db, legal)
    assert [item["id"] for item in queue] == [review_id]
    with pytest.raises(ValueError, match="状态不允许"):
        review_service.create_ai_review(db, "material-1")
    db.close()


def test_background_review_failure_is_persisted_and_material_recovers(monkeypatch):
    factory = _session_factory()
    _seed(factory)
    monkeypatch.setattr(review_service, "SessionLocal", factory)

    def fail_pipeline(*_args):
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(review_service, "run_review_pipeline", fail_pipeline)

    db = factory()
    review, _ = review_service.create_ai_review(db, "material-1")
    db.close()
    review_service.execute_ai_review(review.id)

    db = factory()
    stored = db.query(Review).filter(Review.id == review.id).one()
    material = db.query(Material).filter(Material.id == "material-1").one()
    assert stored.task_status == "failed"
    assert "upstream unavailable" in stored.error_message
    assert material.status == MaterialStatus.draft
    db.close()


def test_legal_failure_is_not_completed_when_public_opinion_succeeds(monkeypatch):
    factory = _session_factory()
    _seed(factory)
    monkeypatch.setattr(review_service, "SessionLocal", factory)
    monkeypatch.setattr(review_service, "run_review_pipeline", lambda *_args: (_ for _ in ()).throw(RuntimeError("legal unavailable")))
    monkeypatch.setattr(
        review_service,
        "run_public_opinion_review",
        lambda **_kwargs: PublicOpinionReview(
            status="completed", result={"risk_level": "low"}, safety_score=90
        ),
    )

    db = factory()
    review, _ = review_service.create_ai_review(db, "material-1")
    db.close()


def test_startup_recovery_marks_stale_work_retryable(monkeypatch):
    factory = _session_factory()
    _seed(factory)
    monkeypatch.setattr(review_service, "SessionLocal", factory)
    db = factory()
    material = db.query(Material).filter(Material.id == "material-1").one()
    material.status = MaterialStatus.ai_reviewing
    review = Review(material_id=material.id, task_status="processing", created_at=datetime.now(timezone.utc) - timedelta(minutes=16))
    db.add(review)
    db.commit()
    review_id = review.id
    material_id = material.id
    db.close()

    assert review_service.recover_interrupted_reviews() == 1

    db = factory()
    assert db.query(Review).filter(Review.id == review_id).one().task_status == "failed"
    assert db.query(Material).filter(Material.id == material_id).one().status == MaterialStatus.draft
    db.close()
    review_service.execute_ai_review(review.id)

    db = factory()
    stored = db.query(Review).filter(Review.id == review.id).one()
    material = db.query(Material).filter(Material.id == "material-1").one()
    assert stored.task_status == "failed"
    assert material.status == MaterialStatus.draft
    db.close()
