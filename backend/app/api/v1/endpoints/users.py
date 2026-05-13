"""用户管理端点 —— 当前为占位，待接入真实用户系统。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class UserProfile(BaseModel):
    """用户个人信息模型：用户 ID、用户名和邮箱。"""
    id: str
    username: str
    email: str = ""


@router.get("/me", response_model=UserProfile)
async def get_current_user():
    """获取当前登录用户信息（占位）—— 返回用户个人资料。"""
    raise HTTPException(status_code=501, detail="User management not yet implemented")
