"""API v1 主路由 —— 聚合所有端点子路由。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, review, users

api_router = APIRouter()  # v1 版本下所有功能模块的路由聚合入口

api_router.include_router(health.router, prefix="/health", tags=["health"])  # 健康检查
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])  # 认证授权
api_router.include_router(users.router, prefix="/users", tags=["users"])  # 用户管理
api_router.include_router(review.router, prefix="/review", tags=["review"])  # 广告审查
