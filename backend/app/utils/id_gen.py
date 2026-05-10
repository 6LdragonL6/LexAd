"""ID generation utilities."""

import uuid
from datetime import datetime, timezone


def generate_request_id() -> str:
    return uuid.uuid4().hex[:12]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
