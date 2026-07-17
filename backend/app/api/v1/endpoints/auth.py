from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import LoginRequest, TokenResponse, UserOut
from app.services.auth import authenticate_user, create_user_token
from app.api.deps import get_current_user
from app.models.user import User
from app.core.rate_limit import (
    check_login_allowed,
    clear_username_login_failures,
    record_failed_login,
)

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    check_login_allowed(request, body.username)
    user = authenticate_user(db, body.username, body.password)
    if not user:
        record_failed_login(request, body.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账户或密码错误")
    clear_username_login_failures(body.username)
    token = create_user_token(user)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
