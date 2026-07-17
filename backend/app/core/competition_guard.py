"""竞赛公开部署保护：锁定基础资料和服务器端 AI 配置。"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings


_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_KNOWLEDGE_PREFIX = "/api/v1/admin/knowledge"
_AI_SETTINGS_PREFIX = "/api/v1/admin/settings/ai"
_RECYCLE_BIN_PREFIX = "/api/v1/admin/settings/recycle-bin"


class CompetitionGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        if settings.COMPETITION_MODE and _is_protected_write(request):
            response: Response = JSONResponse(
                status_code=403,
                content={
                    "detail": "竞赛保护模式已开启：基础资料、回收站与服务器 AI 配置为只读",
                    "code": "competition_mode_read_only",
                },
            )
        else:
            response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if settings.APP_ENV == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def _is_protected_write(request: Request) -> bool:
    if request.method.upper() in _SAFE_METHODS:
        return False
    path = request.url.path.rstrip("/")
    return any(
        path.startswith(prefix)
        for prefix in (_KNOWLEDGE_PREFIX, _AI_SETTINGS_PREFIX, _RECYCLE_BIN_PREFIX)
    )
