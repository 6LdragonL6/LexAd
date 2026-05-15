from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import case
from app.models.material import Material, MaterialStatus
from app.models.review import Review, LegalDecision
from app.models.user import User, UserRole
from app.schemas.review import LegalDecisionRequest
from app.engine.pipeline import run_review_pipeline


def trigger_ai_review(db: Session, material_id: str) -> Review:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise ValueError("Material not found")

    material.status = MaterialStatus.ai_reviewing
    db.commit()

    engine_result = run_review_pipeline(material.raw_text, material.industry, material.platforms)

    review = Review(
        material_id=material_id,
        version=material.current_version,
        ai_risk_score=engine_result.risk_score,
        ai_result=engine_result.model_dump(),
    )
    db.add(review)
    material.status = MaterialStatus.pending_legal
    db.commit()
    db.refresh(review)
    return review


def get_review(db: Session, review_id: str) -> Review | None:
    return db.query(Review).filter(Review.id == review_id).first()


def get_latest_review_by_material(db: Session, material_id: str) -> Review | None:
    return db.query(Review).filter(Review.material_id == material_id).order_by(Review.version.desc()).first()


def submit_legal_decision(db: Session, review_id: str, data: LegalDecisionRequest, reviewer: User) -> Review:
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise ValueError("Review not found")

    material = db.query(Material).filter(Material.id == review.material_id).first()
    review.legal_decision = LegalDecision(data.decision)
    review.legal_notes = data.notes
    review.return_reasons = data.return_reasons
    review.reviewer_id = reviewer.id
    review.reviewed_at = datetime.now(timezone.utc)

    if data.decision == "approved":
        material.status = MaterialStatus.approved
    elif data.decision in ("returned", "conditional"):
        material.status = MaterialStatus.returned
    db.commit()
    db.refresh(review)
    return review


def get_legal_queue(db: Session, user: User) -> list[dict]:
    query = db.query(Review).join(Material, Review.material_id == Material.id)

    if user.role == UserRole.marketing:
        query = query.filter(Material.submitter_id == user.id)
    else:
        query = query.filter(Material.status.in_([MaterialStatus.pending_legal, MaterialStatus.in_legal_review]))

    priority_order = case(
        (Material.priority == "extreme", 0),
        (Material.priority == "urgent", 1),
        else_=2,
    )
    query = query.order_by(priority_order, Review.created_at.desc())

    results = []
    for review in query.all():
        material = db.query(Material).filter(Material.id == review.material_id).first()
        submitter = db.query(User).filter(User.id == material.submitter_id).first()
        results.append({
            "id": review.id,
            "material_id": material.id,
            "material_name": material.name,
            "submitter_name": submitter.display_name if submitter else "",
            "industry": material.industry,
            "ai_risk_score": review.ai_risk_score,
            "priority": material.priority.value,
            "status": material.status.value,
            "created_at": review.created_at,
            "waiting_hours": round((datetime.now(timezone.utc) - review.created_at).total_seconds() / 3600, 1),
        })
    return results
