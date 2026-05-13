"""认证端点 —— 当前为占位，待接入真实用户认证系统。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class LoginRequest(BaseModel):
    """登录请求体：用户名和密码。"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """登录令牌响应体：访问令牌和令牌类型。"""
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(_body: LoginRequest):
    """登录接口（占位）—— 验证用户凭据并返回 JWT 令牌。"""
    raise HTTPException(status_code=501, detail="Authentication not yet implemented")


@router.post("/register")
async def register():
    """注册接口（占位）—— 创建新用户账号。"""
    raise HTTPException(status_code=501, detail="Registration not yet implemented")
