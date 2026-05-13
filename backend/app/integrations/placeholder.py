"""第三方集成适配器层 —— 封装外部 API 调用（DeepSeek、支付、通知等）。

每个集成都应通过清晰的接口进行隔离。
"""

from __future__ import annotations


class BaseIntegration:
    """所有第三方集成适配器的基类。"""
    pass
