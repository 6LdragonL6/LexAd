"""Small, deterministic Chinese text similarity helpers used when no model is available."""

from __future__ import annotations

import re


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").lower())


def char_ngrams(value: str, size: int = 2) -> set[str]:
    normalized = normalize_text(value)
    if len(normalized) < size:
        return {normalized} if normalized else set()
    return {normalized[index:index + size] for index in range(len(normalized) - size + 1)}


def similarity(left: str, right: str) -> float:
    left_grams = char_ngrams(left)
    right_grams = char_ngrams(right)
    if not left_grams or not right_grams:
        return 0.0
    return len(left_grams & right_grams) / len(left_grams | right_grams)


def shared_phrase(left: str, right: str, min_length: int = 2, max_length: int = 12) -> str:
    source = normalize_text(left)
    target = normalize_text(right)
    best = ""
    for start in range(len(source)):
        for end in range(start + min_length, min(len(source), start + max_length) + 1):
            candidate = source[start:end]
            if len(candidate) > len(best) and candidate in target:
                best = candidate
    return best
