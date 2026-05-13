"""LexAd —— 广告合规审查平台。

FastAPI 应用入口，配置 API 版本管理、CORS 跨域和全局异常处理。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import LexAdError
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化日志，关闭时清理资源。"""
    setup_logging()
    yield


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用（CORS、异常处理、路由注册）。"""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="广告合规审查平台",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # ── CORS 跨域配置 ────────────────────────────────────────────────────────
    origins = [settings.FRONTEND_ORIGIN]
    if settings.CORS_ORIGINS:
        origins.extend(o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 全局异常处理器 ───────────────────────────────────────────────────────
    @app.exception_handler(LexAdError)
    async def lexad_error_handler(_: Request, exc: LexAdError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # ── 注册路由 ─────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── 健康检查（在版本化 API 之外） ─────────────────────────────────────────
    @app.get("/health")
    async def health():
        """健康检查端点，返回应用运行状态。"""
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    return app


# 模块级应用实例（供 uvicorn 直接引用）
app = create_app()
