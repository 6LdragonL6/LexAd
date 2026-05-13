"""安全工具模块 —— JWT 令牌的生成与验证。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt
from jose.exceptions import JWTError

from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"  # JWT 签名算法


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建 JWT 访问令牌，嵌入过期时间并使用 HS256 签名。"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> dict | None:
    """验证 JWT 访问令牌，解码成功返回 payload，失败返回 None。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
