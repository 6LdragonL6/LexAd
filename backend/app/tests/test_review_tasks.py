"""Background review task state regression tests."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.db.base import Base
from app.models.material import Material, MaterialStatus
from app.models.review import Review
from app.models.user import User, UserRole
from app.schemas.review import EngineResult
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
    monkeypatch.setattr(
        review_service,
        "run_review_pipeline",
        lambda *_args: EngineResult(risk_score=95, summary="测试完成"),
    )

    db = factory()
    review, created = review_service.create_ai_review(db, "material-1")
    duplicate, duplicate_created = review_service.create_ai_review(db, "material-1")
    assert created is True
    assert duplicate_created is False
    assert duplicate.id == review.id
    db.close()

    review_service.execute_ai_review(review.id)

    db = factory()
    stored = db.query(Review).filter(Review.id == review.id).one()
    material = db.query(Material).filter(Material.id == "material-1").one()
    assert stored.task_status == "completed"
    assert stored.ai_risk_score == 95
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
    assert [item["id"] for item in queue] == [review.id]
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
