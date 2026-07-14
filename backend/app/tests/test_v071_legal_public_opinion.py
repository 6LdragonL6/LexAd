import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.knowledge import ReviewModuleStatus
from app.models.material import Material, MaterialStatus
from app.models.review import Review
from app.models.user import User, UserRole
from app.schemas.review import LegalDecisionRequest
from app.services import review_service


def test_legal_decision_waits_for_public_opinion_or_manual_review():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        market = User(id="market", username="market", password="x", display_name="市场", role=UserRole.marketing, dept_name="市场部")
        legal = User(id="legal", username="legal", password="x", display_name="法务", role=UserRole.legal, dept_name="法务部")
        material = Material(
            id="material",
            name="物料",
            display_name="物料",
            submitter_id=market.id,
            status=MaterialStatus.pending_legal,
        )
        review = Review(
            id="review",
            material_id=material.id,
            task_status="completed",
            legal_module_status=ReviewModuleStatus.succeeded,
            public_opinion_module_status=ReviewModuleStatus.pending,
        )
        db.add_all([market, legal, material, review])
        db.commit()

        with pytest.raises(ValueError, match="仍在处理中"):
            review_service.submit_legal_decision(db, review.id, LegalDecisionRequest(decision="approved"), legal)

        review.public_opinion_module_status = ReviewModuleStatus.failed
        db.commit()
        with pytest.raises(ValueError, match="人工舆情复核"):
            review_service.submit_legal_decision(db, review.id, LegalDecisionRequest(decision="approved"), legal)

        review.public_opinion_module_status = ReviewModuleStatus.succeeded
        review.public_opinion_result = {"status": "manual_review", "requires_manual_review": True}
        db.commit()
        with pytest.raises(ValueError, match="人工舆情复核"):
            review_service.submit_legal_decision(db, review.id, LegalDecisionRequest(decision="approved"), legal)

        result = review_service.submit_legal_decision(
            db,
            review.id,
            LegalDecisionRequest(decision="approved", public_opinion_manually_reviewed=True),
            legal,
        )
        assert result.legal_decision.value == "approved"
