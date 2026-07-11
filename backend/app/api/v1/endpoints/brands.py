from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_legal_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.brand import BrandCreate, BrandUpdate, BrandCreateResponse, BrandProfile, BrandOut
from app.services import brand_service

router = APIRouter()


@router.get("", response_model=list[BrandOut])
def list_brands(
    search: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return brand_service.search_brands(db, search)


@router.post("", response_model=BrandCreateResponse, status_code=201)
def create_brand(
    body: BrandCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        existing = brand_service.find_by_normalized_name(db, body.name)
        if existing and existing.status.value == "archived":
            raise HTTPException(
                status_code=409,
                detail="同名品牌已归档，请先恢复后再创建",
            )
        return brand_service.create_brand(db, body, user.id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="创建品牌失败")


@router.get("/{brand_id}/profile", response_model=BrandProfile)
def get_profile(
    brand_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return brand_service.get_brand_profile(db, brand_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(
    brand_id: str,
    body: BrandUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_legal_or_admin),
):
    try:
        return brand_service.update_brand(db, brand_id, body)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        if "conflict" in msg.lower() or "blank" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
