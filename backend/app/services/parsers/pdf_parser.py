"""PDF parser — text extraction via PyMuPDF, OCR fallback for scanned pages."""
from __future__ import annotations

from pathlib import Path

from app.services.parsers.text_parser import ExtractionResult


class PdfParser:
    MIME_TYPES = {"application/pdf"}
    MAX_PAGES = 50

    @staticmethod
    def supports(mime: str) -> bool:
        return mime in PdfParser.MIME_TYPES

    @staticmethod
    def parse(file_path: str | Path) -> ExtractionResult:
        import fitz

        path = Path(file_path)
        doc = fitz.open(str(path))
        try:
            if len(doc) > PdfParser.MAX_PAGES:
                raise ValueError(f"PDF 页数超过上限（{PdfParser.MAX_PAGES} 页）")
            texts: list[str] = []

            for page in doc:
                page_text = page.get_text().strip()
                if page_text:
                    texts.append(page_text)

            if texts:
                full_text = "\n".join(texts)
                return ExtractionResult(
                    text=full_text,
                    source_format="pdf_text",
                    quality="good" if len(full_text) > 20 else "degraded",
                    fallback_used=False,
                )

            return _ocr_all_pages(doc)
        finally:
            doc.close()


def _ocr_all_pages(doc) -> ExtractionResult:
    from PIL import Image
    import pytesseract
    import io

    texts: list[str] = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            page_text = pytesseract.image_to_string(img, lang="chi_sim+eng").strip()
        except pytesseract.TesseractNotFoundError:
            page_text = ""
        if page_text:
            texts.append(page_text)

    full_text = "\n".join(texts)
    return ExtractionResult(
        text=full_text,
        source_format="pdf_ocr",
        quality="degraded" if full_text.strip() else "minimal",
        fallback_used=True,
    )
