"""LexAd — Advertising Compliance Review Platform (Demo v0.1.0)

FastAPI application entry point.
Single-service architecture: no frontend/backend split.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import STATIC_DIR
from app.routers.pages import router as pages_router

app = FastAPI(
    title="LexAd",
    description="广告合规审查平台 Demo 第一版",
    version="0.1.0",
)

# Static files (CSS, JS, images, uploads)
static_dir = Path(STATIC_DIR)
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "uploads").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Routes
app.include_router(pages_router)


@app.get("/health")
async def health():
    """Health check endpoint for Render."""
    return {"status": "ok", "app": "LexAd", "version": "0.1.0"}
