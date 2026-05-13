"""统一异常类定义 —— 用于全局异常处理中间件。"""

from __future__ import annotations


class LexAdError(Exception):
    """应用基础异常类，支持自定义 HTTP 状态码和错误详情。"""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None, status_code: int | None = None):
        """创建异常实例，可选覆盖默认的 detail 和 status_code。"""
        if detail:
            self.detail = detail
        if status_code:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(LexAdError):
    """资源未找到异常（404）。"""
    status_code = 404
    detail = "Resource not found"


class ValidationError(LexAdError):
    """输入校验失败异常（422）。"""
    status_code = 422
    detail = "Validation error"


class UnauthorizedError(LexAdError):
    """未认证异常（401）。"""
    status_code = 401
    detail = "Unauthorized"


class ForbiddenError(LexAdError):
    """无权限异常（403）。"""
    status_code = 403
    detail = "Forbidden"
