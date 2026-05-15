from datetime import timedelta

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, verify_access_token
from app.models.user import User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(
        User.username == username, User.is_active == True
    ).first()
    if not user or not verify_password(password, user.password):
        return None
    return user


def create_user_token(user: User) -> str:
    return create_access_token(data={"sub": str(user.id), "role": user.role.value})


def get_token_payload(token: str) -> dict | None:
    return verify_access_token(token)
