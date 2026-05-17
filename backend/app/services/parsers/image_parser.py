"""Image OCR parser using Tesseract + Pillow."""
from __future__ import annotations

import os
from pathlib import Path

from app.services.parsers.text_parser import ExtractionResult


def _configure_tesseract() -> None:
    """Set tesseract_cmd if tesseract is not already on PATH."""
    import pytesseract

    # Already configured or on PATH -- skip
    if getattr(pytesseract.pytesseract, "tesseract_cmd", None) not in (None, "tesseract"):
        return

    # Common install locations on Windows
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return


class ImageParser:
    MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/bmp"}

    @staticmethod
    def supports(mime: str) -> bool:
        return mime in ImageParser.MIME_TYPES

    @staticmethod
    def parse(file_path: str | Path) -> ExtractionResult:
        from PIL import Image
        import pytesseract

        _configure_tesseract()

        path = Path(file_path)
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="chi_sim+eng").strip()
        quality = _assess_ocr_quality(text)
        return ExtractionResult(
            text=text,
            source_format="image_ocr",
            quality=quality,
            fallback_used=False,
        )


def _assess_ocr_quality(text: str) -> str:
    if not text.strip():
        return "minimal"
    if len(text) < 20:
        return "degraded"
    return "good"
