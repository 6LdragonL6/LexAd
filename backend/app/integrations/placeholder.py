"""Third-party integration adapters.

Encapsulate external API calls (DeepSeek, payment gateways, notification services, etc.).
Each integration should be isolated behind a clear interface.
"""

from __future__ import annotations


class BaseIntegration:
    """Base class for all third-party integrations."""
    pass
