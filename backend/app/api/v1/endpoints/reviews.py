from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import ensure_material_visible, get_current_user, require_legal, require_marketing
from app.models.user import User
from app.models.material import Material
from app.schemas.review import AIReviewRequest, ReviewOut, LegalDecisionRequest, ReviewQueueItem
from app.services import review_service
from app.core.rate_limit import enforce_ai_request_limit

router = APIRouter()


@router.post("/ai-review", response_model=ReviewOut, status_code=202)
def trigger_ai_review(
    body: AIReviewRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_marketing),
):
    try:
        material = db.query(Material).filter(Material.id == body.material_id, Material.deleted_at.is_(None)).first()
        if not material:
            raise ValueError("Material not found")
        if user.role.value != "admin" and material.submitter_id != user.id:
            raise HTTPException(status_code=403, detail="只能审查自己提交的物料")
        enforce_ai_request_limit(request, user.id)
        review, created = review_service.create_ai_review(db, body.material_id)
        if created:
            background_tasks.add_task(review_service.execute_ai_review, review.id)
        return review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/queue", response_model=list[ReviewQueueItem])
def get_queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return review_service.get_legal_queue(db, user)


@router.get("/by-material/{material_id}", response_model=ReviewOut)
def get_review_by_material(material_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = db.query(Material).filter(Material.id == material_id, Material.deleted_at.is_(None)).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    ensure_material_visible(user, material)
    review = review_service.get_latest_review_by_material(db, material_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found for this material")
    return review


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    review = review_service.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    material = db.query(Material).filter(Material.id == review.material_id, Material.deleted_at.is_(None)).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    ensure_material_visible(user, material)
    return review


@router.post("/{review_id}/decision", response_model=ReviewOut)
def submit_decision(review_id: str, body: LegalDecisionRequest, db: Session = Depends(get_db), user: User = Depends(require_legal)):
    try:
        review = review_service.submit_legal_decision(db, review_id, body, user)
        return review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
