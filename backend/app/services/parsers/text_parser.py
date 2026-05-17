"""TXT file parser with encoding detection."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractionResult:
    text: str
    source_format: str
    quality: str  # "good" | "degraded" | "minimal"
    fallback_used: bool


class TextParser:
    MIME_TYPES = {"text/plain"}

    @staticmethod
    def supports(mime: str) -> bool:
        return mime in TextParser.MIME_TYPES

    @staticmethod
    def parse(file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)
        raw = path.read_bytes()
        text = _decode_bytes(raw)
        quality = "good" if text.strip() else "minimal"
        return ExtractionResult(
            text=text.strip(),
            source_format="txt_raw",
            quality=quality,
            fallback_used=False,
        )


def _decode_bytes(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("gbk")
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("gb2312")
    except UnicodeDecodeError:
        pass
    return raw.decode("latin-1")
