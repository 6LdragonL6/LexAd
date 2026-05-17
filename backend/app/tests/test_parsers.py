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
