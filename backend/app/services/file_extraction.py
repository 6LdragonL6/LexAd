"""File extraction service — dispatches to format-specific parsers with OCR fallback."""
from __future__ import annotations

from pathlib import Path
import mimetypes

from app.services.parsers.text_parser import ExtractionResult, TextParser
from app.services.parsers.image_parser import ImageParser
from app.services.parsers.pdf_parser import PdfParser
from app.services.parsers.office_parser import OfficeParser


class ExtractionError(Exception):
    pass


class FileExtractionService:
    ALLOWED_MIMES = {
        *TextParser.MIME_TYPES,
        *ImageParser.MIME_TYPES,
        *PdfParser.MIME_TYPES,
        *OfficeParser.MIME_TYPES,
    }

    PARSERS = [TextParser, ImageParser, PdfParser, OfficeParser]

    def is_supported(self, mime: str) -> bool:
        return mime in self.ALLOWED_MIMES

    def mime_from_extension(self, filename: str) -> str:
        mime, _ = mimetypes.guess_type(filename)
        if mime:
            return mime
        ext = Path(filename).suffix.lower()
        overrides = {
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".doc": "application/msword",
        }
        return overrides.get(ext, "application/octet-stream")

    @staticmethod
    def extract(file_path: str | Path, mime: str) -> ExtractionResult:
        path = Path(file_path)
        if not path.exists() or path.stat().st_size == 0:
            raise ExtractionError("文件为空或无法读取")

        parser = _find_parser(mime)
        if parser is None:
            raise ExtractionError(f"不支持的文件格式: {mime}")

        try:
            if parser is OfficeParser:
                return parser.parse(path, mime)
            return parser.parse(path)
        except ExtractionError:
            raise
        except Exception:
            return _ocr_fallback(path)


def _find_parser(mime: str):
    for parser_cls in FileExtractionService.PARSERS:
        if parser_cls.supports(mime):
            return parser_cls
    return None


def _ocr_fallback(file_path: str | Path) -> ExtractionResult:
    try:
        return ImageParser.parse(file_path)
    except Exception:
        raise ExtractionError("无法提取文本，建议手动输入广告文案内容")
