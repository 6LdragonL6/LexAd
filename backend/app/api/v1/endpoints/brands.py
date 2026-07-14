from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin, require_legal_or_admin
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.brand import (
    BrandCreate,
    BrandIndustrySuggestionAction,
    BrandIndustryUpdate,
    BrandUpdate,
    BrandCreateResponse,
    BrandProfile,
    BrandOut,
)
from app.services import brand_service

router = APIRouter()


@router.get("", response_model=list[BrandOut])
def list_brands(
    search: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return brand_service.search_brands(db, search, include_archived=user.role == UserRole.admin)


@router.post("", response_model=BrandCreateResponse, status_code=201)
def create_brand(
    body: BrandCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        existing = brand_service.find_by_normalized_name(db, body.name, include_deleted=True)
        if existing and existing.deleted_at is not None:
            raise HTTPException(
                status_code=409,
                detail="同名品牌位于回收站，请先恢复或永久删除",
            )
        if existing and existing.status.value == "archived":
            raise HTTPException(
                status_code=409,
                detail="同名品牌已归档，请先恢复后再创建",
            )
        return brand_service.create_brand(db, body, user.id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="创建品牌失败")


@router.get("/{brand_id}/profile", response_model=BrandProfile)
def get_profile(
    brand_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return brand_service.get_brand_profile(db, brand_id, include_suggestions=user.role == UserRole.admin)
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
        if body.industry is not None:
            raise HTTPException(status_code=422, detail="请使用标准行业多选维护品牌行业")
        if body.industries is not None and user.role != UserRole.admin:
            raise HTTPException(status_code=403, detail="只有管理员可以维护品牌行业")
        return brand_service.update_brand(db, brand_id, body, user.id)
    except HTTPException:
        raise
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        if "conflict" in msg.lower() or "blank" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.put("/{brand_id}/industries", response_model=BrandOut)
def set_brand_industries(
    brand_id: str,
    body: BrandIndustryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    try:
        return brand_service.set_brand_industries(db, brand_id, body.industries, user.id)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 422
        raise HTTPException(status_code=status_code, detail=str(exc))


@router.post("/{brand_id}/industry-suggestions/{suggestion_id}", response_model=BrandProfile)
def review_brand_industry_suggestion(
    brand_id: str,
    suggestion_id: str,
    body: BrandIndustrySuggestionAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    try:
        brand_service.review_industry_suggestion(db, brand_id, suggestion_id, body.action, user.id)
        return brand_service.get_brand_profile(db, brand_id, include_suggestions=True)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 422
        raise HTTPException(status_code=status_code, detail=str(exc))
