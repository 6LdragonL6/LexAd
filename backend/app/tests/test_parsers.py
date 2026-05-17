"""Tests for file format parsers."""
import tempfile
from pathlib import Path
from app.services.parsers.text_parser import TextParser


class TestTextParser:
    def test_supports_txt(self):
        assert TextParser.supports("text/plain") is True

    def test_parse_utf8(self):
        content = "这是广告文案内容\n包含多行文本"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            tmp_path = Path(f.name)

        try:
            result = TextParser.parse(tmp_path)
            # Normalize line endings for cross-platform compatibility
            assert result.text.replace("\r\n", "\n").strip() == content.strip()
            assert result.source_format == "txt_raw"
            assert result.quality == "good"
            assert result.fallback_used is False
        finally:
            tmp_path.unlink()

    def test_parse_gbk(self):
        content = "GBK编码的广告文案"
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".txt", delete=False
        ) as f:
            f.write(content.encode("gbk"))
            tmp_path = Path(f.name)

        try:
            result = TextParser.parse(tmp_path)
            assert content in result.text
            assert result.quality == "good"
        finally:
            tmp_path.unlink()

    def test_parse_empty_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = Path(f.name)

        try:
            result = TextParser.parse(tmp_path)
            assert result.text == ""
            assert result.quality == "minimal"
        finally:
            tmp_path.unlink()


class TestImageParser:
    def test_supports_image_mimes(self):
        from app.services.parsers.image_parser import ImageParser
        assert ImageParser.supports("image/png") is True
        assert ImageParser.supports("image/jpeg") is True
        assert ImageParser.supports("image/gif") is True
        assert ImageParser.supports("image/bmp") is True
        assert ImageParser.supports("video/mp4") is False

    def test_parse_creates_result(self):
        from app.services.parsers.image_parser import ImageParser
        from PIL import Image
        import tempfile
        from pathlib import Path

        img = Image.new("RGB", (200, 50), color="white")
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp)
        tmp.close()
        tmp_path = Path(tmp.name)

        try:
            result = ImageParser.parse(tmp_path)
            assert result.source_format == "image_ocr"
            assert result.quality in ("good", "degraded", "minimal")
            assert isinstance(result.text, str)
        finally:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
