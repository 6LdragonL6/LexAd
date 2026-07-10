from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.auth import get_token_payload
from app.models.user import User, UserRole
from app.models.material import Material, MaterialStatus

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = get_token_payload(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user

def require_legal(user: User = Depends(get_current_user)) -> User:
    if user.role.value not in ("legal", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Legal or admin only")
    return user


def require_marketing(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.marketing, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅市场人员或管理员可以提交和审查物料",
        )
    return user


def can_view_material(user: User, material: Material) -> bool:
    if user.role == UserRole.admin:
        return True
    if user.role == UserRole.marketing:
        return material.submitter_id == user.id
    return material.status in {
        MaterialStatus.pending_legal,
        MaterialStatus.in_legal_review,
        MaterialStatus.approved,
        MaterialStatus.conditional_approved,
        MaterialStatus.returned,
        MaterialStatus.archived,
    }


def ensure_material_visible(user: User, material: Material) -> None:
    if not can_view_material(user, material):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该物料",
        )
