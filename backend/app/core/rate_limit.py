"""轻量级进程内限流，适用于 Render 单实例竞赛部署。"""

from __future__ import annotations

from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


class SlidingWindowLimiter:
    """线程安全的滑动窗口计数器。服务重启后自动清空。"""

    def __init__(self) -> None:
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def retry_after(self, scope: str, key: str, limit: int, window_seconds: int) -> int | None:
        now = monotonic()
        bucket_key = (scope, key)
        with self._lock:
            events = self._events[bucket_key]
            self._discard_expired(events, now, window_seconds)
            if len(events) < limit:
                if not events:
                    self._events.pop(bucket_key, None)
                return None
            return max(1, ceil(window_seconds - (now - events[0])))

    def consume(self, scope: str, key: str, limit: int, window_seconds: int) -> int | None:
        now = monotonic()
        bucket_key = (scope, key)
        with self._lock:
            events = self._events[bucket_key]
            self._discard_expired(events, now, window_seconds)
            if len(events) >= limit:
                return max(1, ceil(window_seconds - (now - events[0])))
            events.append(now)
            return None

    def reset(self, scope: str, key: str) -> None:
        with self._lock:
            self._events.pop((scope, key), None)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    @staticmethod
    def _discard_expired(events: deque[float], now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()


_limiter = SlidingWindowLimiter()


def check_login_allowed(request: Request, username: str) -> None:
    settings = get_settings()
    checks = (
        ("login-ip", _client_key(request)),
        ("login-username", _username_key(username)),
    )
    for scope, key in checks:
        retry_after = _limiter.retry_after(
            scope,
            key,
            settings.LOGIN_RATE_LIMIT_ATTEMPTS,
            settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )
        if retry_after is not None:
            _raise_rate_limited("登录尝试过于频繁，请稍后再试", retry_after)


def record_failed_login(request: Request, username: str) -> None:
    settings = get_settings()
    for scope, key in (
        ("login-ip", _client_key(request)),
        ("login-username", _username_key(username)),
    ):
        _limiter.consume(
            scope,
            key,
            settings.LOGIN_RATE_LIMIT_ATTEMPTS,
            settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )


def clear_username_login_failures(username: str) -> None:
    _limiter.reset("login-username", _username_key(username))


def enforce_ai_request_limit(request: Request, user_id: str) -> None:
    settings = get_settings()
    for scope, key in (
        ("ai-ip", _client_key(request)),
        ("ai-user", str(user_id)),
    ):
        retry_after = _limiter.consume(
            scope,
            key,
            settings.AI_RATE_LIMIT_REQUESTS,
            settings.AI_RATE_LIMIT_WINDOW_SECONDS,
        )
        if retry_after is not None:
            _raise_rate_limited("AI 审查请求过于频繁，请稍后再试", retry_after)


def reset_rate_limits() -> None:
    """供测试和运维自检使用，不对外暴露。"""
    _limiter.clear()


def _client_key(request: Request) -> str:
    # Render sets X-Forwarded-For. Username/user-id buckets remain authoritative
    # even if a client attempts to spoof this secondary IP bucket.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        candidate = forwarded.split(",", 1)[0].strip()
        if candidate:
            return candidate[:128]
    if request.client and request.client.host:
        return request.client.host[:128]
    return "unknown"


def _username_key(username: str) -> str:
    return username.strip().casefold()[:128] or "<empty>"


def _raise_rate_limited(message: str, retry_after: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=message,
        headers={"Retry-After": str(retry_after)},
    )
