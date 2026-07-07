from __future__ import annotations

import re
from typing import Iterable


INDUSTRY_SEPARATOR = "、"
INDUSTRY_SPLIT_RE = re.compile(r"[、,，;；/|]+")


def split_industries(value: str | Iterable[str] | None) -> list[str]:
    """Normalize the compatible v0.4.2 industry format into a list.

    v0.4.2 keeps Material.industry as a string for database compatibility, but
    the submit UI may join multiple industries with "、". This helper is the
    single parsing point used by review engines.
    """
    if value is None:
        return []
    raw_items: list[str] = []
    if isinstance(value, str):
        raw_items = INDUSTRY_SPLIT_RE.split(value)
    else:
        for item in value:
            raw_items.extend(INDUSTRY_SPLIT_RE.split(str(item)))

    result: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def format_industries(value: str | Iterable[str] | None) -> str:
    return INDUSTRY_SEPARATOR.join(split_industries(value))
