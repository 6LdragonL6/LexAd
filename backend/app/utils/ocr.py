"""OCR utility — local Tesseract placeholder with automatic mock fallback."""

import logging
from pathlib import Path

from app.core.config import get_settings
from app.schemas.models import OCRResult

settings = get_settings()
logger = logging.getLogger(__name__)


def extract_ocr_text(image_path: str) -> OCRResult:
    path = Path(image_path)

    if not path.exists():
        return OCRResult(
            text="",
            status="image_missing",
            provider="tesseract_mock",
            confidence=0.0,
            error_message=f"Image file not found: {image_path}",
        )

    if not settings.TESSERACT_AVAILABLE:
        return OCRResult(
            text="[OCR mock] Image received but Tesseract is not installed.",
            status="mock",
            provider="tesseract_mock",
            confidence=0.0,
            error_message="",
        )

    return OCRResult(
        text="[OCR mock] Tesseract not configured.",
        status="mock",
        provider="tesseract_mock",
        confidence=0.0,
        error_message="",
    )
