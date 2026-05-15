from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user, require_legal
from app.models.user import User
from app.schemas.review import AIReviewRequest, ReviewOut, LegalDecisionRequest, ReviewQueueItem
from app.services import review_service

router = APIRouter()


@router.post("/ai-review", response_model=ReviewOut)
def trigger_ai_review(body: AIReviewRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        review = review_service.trigger_ai_review(db, body.material_id)
        return review
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/queue", response_model=list[ReviewQueueItem])
def get_queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return review_service.get_legal_queue(db, user)


@router.get("/by-material/{material_id}", response_model=ReviewOut)
def get_review_by_material(material_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    review = review_service.get_latest_review_by_material(db, material_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found for this material")
    return review


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    review = review_service.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/{review_id}/decision", response_model=ReviewOut)
def submit_decision(review_id: str, body: LegalDecisionRequest, db: Session = Depends(get_db), user: User = Depends(require_legal)):
    try:
        review = review_service.submit_legal_decision(db, review_id, body, user)
        return review
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
