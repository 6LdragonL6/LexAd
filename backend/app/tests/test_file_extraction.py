"""Tests for FileExtractionService."""
import tempfile
from pathlib import Path

from app.services.file_extraction import FileExtractionService, ExtractionError


class TestFileExtractionService:
    def test_extract_text_file(self):
        svc = FileExtractionService()
        content = "测试广告文案"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            tmp_path = str(Path(f.name))

        try:
            result = svc.extract(tmp_path, "text/plain")
            assert result.text.strip() == content
            assert result.source_format == "txt_raw"
        finally:
            Path(tmp_path).unlink()

    def test_extract_unsupported_format_raises(self):
        svc = FileExtractionService()
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"\x00\x01\x02")
            tmp_path = str(Path(f.name))

        try:
            svc.extract(tmp_path, "application/octet-stream")
            assert False, "Expected ExtractionError"
        except ExtractionError as e:
            assert "不支持" in str(e)
        finally:
            Path(tmp_path).unlink()

    def test_mime_from_extension(self):
        svc = FileExtractionService()
        assert svc.mime_from_extension("test.pdf") == "application/pdf"
        assert svc.mime_from_extension("test.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert svc.mime_from_extension("test.png") == "image/png"
        assert svc.mime_from_extension("test.pptx") == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert svc.mime_from_extension("test.xlsx") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_allowed_mime(self):
        svc = FileExtractionService()
        assert svc.is_supported("image/png") is True
        assert svc.is_supported("application/pdf") is True
        assert svc.is_supported("video/mp4") is False
