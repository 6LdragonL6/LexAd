"""LexAd — Advertising Compliance Review Platform.

FastAPI application entry point with API versioning, CORS, and middleware.
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
    setup_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="广告合规审查平台",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────────
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

    # ── Exception handler ───────────────────────────────────────────────────
    @app.exception_handler(LexAdError)
    async def lexad_error_handler(_: Request, exc: LexAdError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # ── Routes ──────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── Health check (outside versioned API) ────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    return app


app = create_app()
