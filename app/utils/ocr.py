"""OCR utility — local Tesseract placeholder with automatic mock fallback.

When Tesseract is not installed, returns empty/mock results so the application
starts and runs without errors.  Install Tesseract and set TESSERACT_AVAILABLE = True
in core/config.py to enable real OCR.

Installation guide (Windows):
  Download from https://github.com/UB-Mannheim/tesseract/wiki
  Add to PATH, or set the full path in core/config.py.

Installation guide (macOS):
  brew install tesseract

Installation guide (Linux):
  sudo apt install tesseract-ocr
"""

import logging
from pathlib import Path

from app.core.config import TESSERACT_AVAILABLE
from app.schemas.models import OCRResult

logger = logging.getLogger(__name__)


def extract_ocr_text(image_path: str) -> OCRResult:
    """Extract text from an image via local Tesseract.

    Falls back to mock output when Tesseract is not installed or the image
    file is missing.
    """
    path = Path(image_path)

    if not path.exists():
        return OCRResult(
            text="",
            status="image_missing",
            provider="tesseract_mock",
            confidence=0.0,
            error_message=f"Image file not found: {image_path}",
        )

    if not TESSERACT_AVAILABLE:
        # TODO: Replace with real Tesseract call when installed.
        #   import pytesseract
        #   from PIL import Image
        #   img = Image.open(image_path)
        #   text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return OCRResult(
            text="[OCR mock] Image received but Tesseract is not installed.",
            status="mock",
            provider="tesseract_mock",
            confidence=0.0,
            error_message="",
        )

    # TODO: Real Tesseract path — uncomment and test after installing Tesseract.
    # try:
    #     import pytesseract
    #     from PIL import Image
    #     img = Image.open(image_path)
    #     text = pytesseract.image_to_string(img, lang="chi_sim+eng")
    #     return OCRResult(
    #         text=text.strip(),
    #         status="ok",
    #         provider="tesseract",
    #         confidence=0.0,
    #         error_message="",
    #     )
    # except Exception as e:
    #     logger.exception("Tesseract OCR failed")
    #     return OCRResult(
    #         text="",
    #         status="error",
    #         provider="tesseract",
    #         confidence=0.0,
    #         error_message=str(e),
    #     )

    return OCRResult(
        text="[OCR mock] Tesseract not configured.",
        status="mock",
        provider="tesseract_mock",
        confidence=0.0,
        error_message="",
    )
