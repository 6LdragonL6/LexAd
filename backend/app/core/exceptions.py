"""Unified exception classes and handlers."""

from __future__ import annotations


class LexAdError(Exception):
    """Base exception for the application."""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None, status_code: int | None = None):
        if detail:
            self.detail = detail
        if status_code:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(LexAdError):
    status_code = 404
    detail = "Resource not found"


class ValidationError(LexAdError):
    status_code = 422
    detail = "Validation error"


class UnauthorizedError(LexAdError):
    status_code = 401
    detail = "Unauthorized"


class ForbiddenError(LexAdError):
    status_code = 403
    detail = "Forbidden"
