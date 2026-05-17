# LexAd File Upload & Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add file upload with multi-format text extraction (OCR/PDF/Office/TXT) to the material submission flow, with preview-and-edit before review.

**Architecture:** Backend adds a `FileExtractionService` that dispatches to format-specific parsers (image/PDF/office/text) with auto-fallback to OCR. Frontend adds a drop zone that can preview extracted text before bundling it with the existing textarea content into a multipart `POST /submit`.

**Tech Stack:** FastAPI (async multipart), PyMuPDF, python-docx, python-pptx, openpyxl, Tesseract/Pillow (existing), Vue 3 + TypeScript

---

## File Structure

```
backend/app/services/
  file_extraction.py          NEW — ExtractionResult dataclass + FileExtractionService
  parsers/
    __init__.py               NEW — package init
    image_parser.py           NEW — OCR via Tesseract+Pillow
    pdf_parser.py             NEW — PyMuPDF text extraction, OCR fallback
    office_parser.py          NEW — DOCX/DOC/PPTX/XLSX text extraction
    text_parser.py            NEW — TXT with encoding detection

backend/app/schemas/material.py     MODIFY — raw_text default ""
backend/app/api/v1/endpoints/materials.py  MODIFY — async multipart submit + preview-text
backend/app/services/material_service.py   MODIFY — integrate FileExtractionService
backend/app/storage/__init__.py            MODIFY — temp file helpers

frontend/src/types/index.ts     MODIFY — PreviewTextResponse
frontend/src/api/materials.ts   MODIFY — FormData submit, previewText()
frontend/src/pages/SubmitPage.vue  MODIFY — file drop zone, preview, edit
```

---

### Task 1: Install new Python dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add dependencies to requirements.txt**

```diff
+ PyMuPDF>=1.23.0
+ python-docx>=1.1.0
+ python-pptx>=0.6.21
+ openpyxl>=3.1.0
```

- [ ] **Step 2: Install dependencies**

Run: `cd backend && pip install PyMuPDF python-docx python-pptx openpyxl`

- [ ] **Step 3: Verify imports work**

Run: `python -c "import fitz; import docx; import pptx; import openpyxl; print('All OK')"`
Expected: `All OK`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "build: add file parsing dependencies (PyMuPDF, python-docx, python-pptx, openpyxl)"
```

---

### Task 2: Create parsers package and text parser

**Files:**
- Create: `backend/app/services/parsers/__init__.py`
- Create: `backend/app/services/parsers/text_parser.py`

- [ ] **Step 1: Write tests for text parser**

Create `backend/app/tests/test_parsers.py`:

```python
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
            assert result.text.strip() == content.strip()
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest app/tests/test_parsers.py::TestTextParser -v`
Expected: FAIL — `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Create parsers `__init__.py`**

```python
"""File format parsers — each parser handles one or more MIME types."""
```

- [ ] **Step 4: Create `text_parser.py`**

```python
"""TXT file parser with encoding detection."""
from __future__ import annotations

import re
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_parsers.py::TestTextParser -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/parsers/__init__.py backend/app/services/parsers/text_parser.py backend/app/tests/test_parsers.py
git commit -m "feat: add text parser with UTF-8/GBK encoding detection"
```

---

### Task 3: Create image (OCR) parser

**Files:**
- Create: `backend/app/services/parsers/image_parser.py`
- Modify: `backend/app/tests/test_parsers.py` (append tests)

- [ ] **Step 1: Add image parser tests**

Append to `backend/app/tests/test_parsers.py`:

```python
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

        img = Image.new("RGB", (200, 50), color="white")
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp.name)
        tmp_path = Path(tmp.name)

        try:
            result = ImageParser.parse(tmp_path)
            assert result.source_format == "image_ocr"
            assert result.quality in ("good", "degraded", "minimal")
            assert isinstance(result.text, str)
        finally:
            tmp_path.unlink()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest app/tests/test_parsers.py::TestImageParser -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Create `image_parser.py`**

```python
"""Image OCR parser using Tesseract + Pillow."""
from __future__ import annotations

from pathlib import Path

from app.services.parsers.text_parser import ExtractionResult


class ImageParser:
    MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/bmp"}

    @staticmethod
    def supports(mime: str) -> bool:
        return mime in ImageParser.MIME_TYPES

    @staticmethod
    def parse(file_path: str | Path) -> ExtractionResult:
        from PIL import Image
        import pytesseract

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_parsers.py::TestImageParser -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/parsers/image_parser.py backend/app/tests/test_parsers.py
git commit -m "feat: add image OCR parser via Tesseract"
```

---

### Task 4: Create PDF parser

**Files:**
- Create: `backend/app/services/parsers/pdf_parser.py`
- Modify: `backend/app/tests/test_parsers.py` (append tests)

- [ ] **Step 1: Add PDF parser tests**

Append to `backend/app/tests/test_parsers.py`:

```python
class TestPdfParser:
    def test_supports_pdf(self):
        from app.services.parsers.pdf_parser import PdfParser
        assert PdfParser.supports("application/pdf") is True

    def test_parse_text_pdf(self):
        from app.services.parsers.pdf_parser import PdfParser
        import fitz

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "广告文案测试内容", fontsize=12)
        doc.save(tmp.name)
        doc.close()
        tmp_path = Path(tmp.name)

        try:
            result = PdfParser.parse(tmp_path)
            assert "广告文案测试内容" in result.text
            assert result.source_format == "pdf_text"
            assert result.quality == "good"
            assert result.fallback_used is False
        finally:
            tmp_path.unlink()

    def test_parse_empty_pdf_falls_back_to_ocr(self):
        from app.services.parsers.pdf_parser import PdfParser
        import fitz

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        doc = fitz.open()
        doc.new_page()  # empty page, no text
        doc.save(tmp.name)
        doc.close()
        tmp_path = Path(tmp.name)

        try:
            result = PdfParser.parse(tmp_path)
            assert result.source_format == "pdf_ocr"
            assert result.fallback_used is True
        finally:
            tmp_path.unlink()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest app/tests/test_parsers.py::TestPdfParser -v`
Expected: FAIL

- [ ] **Step 3: Create `pdf_parser.py`**

```python
"""PDF parser — text extraction via PyMuPDF, OCR fallback for scanned pages."""
from __future__ import annotations

from pathlib import Path

from app.services.parsers.text_parser import ExtractionResult


class PdfParser:
    MIME_TYPES = {"application/pdf"}

    @staticmethod
    def supports(mime: str) -> bool:
        return mime in PdfParser.MIME_TYPES

    @staticmethod
    def parse(file_path: str | Path) -> ExtractionResult:
        import fitz

        path = Path(file_path)
        doc = fitz.open(str(path))
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

        # No embedded text — fallback to OCR
        return _ocr_all_pages(doc)


def _ocr_all_pages(doc) -> ExtractionResult:
    from PIL import Image
    import pytesseract
    import io

    texts: list[str] = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        page_text = pytesseract.image_to_string(img, lang="chi_sim+eng").strip()
        if page_text:
            texts.append(page_text)

    full_text = "\n".join(texts)
    return ExtractionResult(
        text=full_text,
        source_format="pdf_ocr",
        quality="degraded" if full_text.strip() else "minimal",
        fallback_used=True,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_parsers.py::TestPdfParser -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/parsers/pdf_parser.py backend/app/tests/test_parsers.py
git commit -m "feat: add PDF parser with PyMuPDF text extraction and OCR fallback"
```

---

### Task 5: Create office parser (DOCX/DOC/PPTX/XLSX)

**Files:**
- Create: `backend/app/services/parsers/office_parser.py`
- Modify: `backend/app/tests/test_parsers.py` (append tests)

- [ ] **Step 1: Add office parser tests**

Append to `backend/app/tests/test_parsers.py`:

```python
class TestOfficeParser:
    def test_supports_docx(self):
        from app.services.parsers.office_parser import OfficeParser
        assert OfficeParser.supports("application/vnd.openxmlformats-officedocument.wordprocessingml.document") is True

    def test_supports_pptx(self):
        from app.services.parsers.office_parser import OfficeParser
        assert OfficeParser.supports("application/vnd.openxmlformats-officedocument.presentationml.presentation") is True

    def test_supports_xlsx(self):
        from app.services.parsers.office_parser import OfficeParser
        assert OfficeParser.supports("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") is True

    def test_supports_doc(self):
        from app.services.parsers.office_parser import OfficeParser
        assert OfficeParser.supports("application/msword") is True

    def test_parse_docx(self):
        from app.services.parsers.office_parser import OfficeParser
        from docx import Document

        tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        doc = Document()
        doc.add_paragraph("广告文案第一段")
        doc.add_paragraph("广告文案第二段")
        doc.save(tmp.name)
        tmp_path = Path(tmp.name)

        try:
            result = OfficeParser.parse(tmp_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            assert "广告文案第一段" in result.text
            assert "广告文案第二段" in result.text
            assert result.source_format == "docx_parse"
            assert result.quality == "good"
        finally:
            tmp_path.unlink()

    def test_parse_pptx(self):
        from app.services.parsers.office_parser import OfficeParser
        from pptx import Presentation
        from pptx.util import Inches

        tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = "广告标题"
        prs.save(tmp.name)
        tmp_path = Path(tmp.name)

        try:
            result = OfficeParser.parse(tmp_path, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
            assert "广告标题" in result.text
            assert result.source_format == "pptx_parse"
        finally:
            tmp_path.unlink()

    def test_parse_xlsx(self):
        from app.services.parsers.office_parser import OfficeParser
        from openpyxl import Workbook

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        wb = Workbook()
        ws = wb.active
        ws["A1"] = "产品名称"
        ws["B1"] = "广告文案"
        ws["A2"] = "产品A"
        ws["B2"] = "优质产品宣传语"
        wb.save(tmp.name)
        tmp_path = Path(tmp.name)

        try:
            result = OfficeParser.parse(tmp_path, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            assert "产品名称" in result.text
            assert "优质产品宣传语" in result.text
            assert result.source_format == "xlsx_parse"
        finally:
            tmp_path.unlink()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest app/tests/test_parsers.py::TestOfficeParser -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Create `office_parser.py`**

```python
"""Office document parser — DOCX, DOC, PPTX, XLSX text extraction."""
from __future__ import annotations

from pathlib import Path

from app.services.parsers.text_parser import ExtractionResult


class OfficeParser:
    MIME_TYPES = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    @staticmethod
    def supports(mime: str) -> bool:
        return mime in OfficeParser.MIME_TYPES

    @staticmethod
    def parse(file_path: str | Path, mime: str) -> ExtractionResult:
        path = Path(file_path)
        if "wordprocessingml" in mime:
            return _parse_docx(path)
        elif "presentation" in mime:
            return _parse_pptx(path)
        elif "spreadsheet" in mime:
            return _parse_xlsx(path)
        elif "msword" in mime:
            # .doc (legacy) — try python-docx, fails → raise for OCR fallback
            return _parse_docx(path)
        raise ValueError(f"Unsupported office MIME: {mime}")


def _parse_docx(path: Path) -> ExtractionResult:
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)
    quality = "good" if text else "minimal"
    return ExtractionResult(
        text=text,
        source_format="docx_parse",
        quality=quality,
        fallback_used=False,
    )


def _parse_pptx(path: Path) -> ExtractionResult:
    from pptx import Presentation

    prs = Presentation(str(path))
    texts: list[str] = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = para.text.strip()
                    if t:
                        texts.append(t)
    text = "\n".join(texts)
    quality = "good" if text else "minimal"
    return ExtractionResult(
        text=text,
        source_format="pptx_parse",
        quality=quality,
        fallback_used=False,
    )


def _parse_xlsx(path: Path) -> ExtractionResult:
    from openpyxl import load_workbook

    wb = load_workbook(str(path), read_only=True, data_only=True)
    texts: list[str] = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows(values_only=True):
            row_text = " | ".join(str(cell) for cell in row if cell is not None)
            if row_text.strip():
                texts.append(row_text)
    wb.close()
    text = "\n".join(texts)
    quality = "good" if text else "minimal"
    return ExtractionResult(
        text=text,
        source_format="xlsx_parse",
        quality=quality,
        fallback_used=False,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_parsers.py::TestOfficeParser -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/parsers/office_parser.py backend/app/tests/test_parsers.py
git commit -m "feat: add office parser for DOCX/PPTX/XLSX"
```

---

### Task 6: Create FileExtractionService

**Files:**
- Create: `backend/app/services/file_extraction.py`
- Create: `backend/app/tests/test_file_extraction.py`

- [ ] **Step 1: Write tests for FileExtractionService**

Create `backend/app/tests/test_file_extraction.py`:

```python
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
        assert svc.mime_from_extension("test.ppt") == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert svc.mime_from_extension("test.xls") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_allowed_mime(self):
        svc = FileExtractionService()
        assert svc.is_supported("image/png") is True
        assert svc.is_supported("application/pdf") is True
        assert svc.is_supported("video/mp4") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest app/tests/test_file_extraction.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Create `file_extraction.py`**

```python
"""File extraction service — dispatches to format-specific parsers with OCR fallback."""
from __future__ import annotations

from pathlib import Path
import mimetypes

from app.services.parsers.text_parser import ExtractionResult, TextParser
from app.services.parsers.image_parser import ImageParser
from app.services.parsers.pdf_parser import PdfParser
from app.services.parsers.office_parser import OfficeParser


class ExtractionError(Exception):
    """Raised when text extraction fails entirely."""
    pass


class FileExtractionService:
    ALLOWED_MIMES = {
        *TextParser.MIME_TYPES,
        *ImageParser.MIME_TYPES,
        *PdfParser.MIME_TYPES,
        *OfficeParser.MIME_TYPES,
    }

    PARSERS = [
        TextParser,
        ImageParser,
        PdfParser,
        OfficeParser,
    ]

    def is_supported(self, mime: str) -> bool:
        return mime in self.ALLOWED_MIMES

    def mime_from_extension(self, filename: str) -> str:
        mime, _ = mimetypes.guess_type(filename)
        if mime:
            return mime
        # Fallback mappings for extensions mimetypes doesn't know
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
            return parser.parse(path, mime) if parser is OfficeParser else parser.parse(path)
        except ExtractionError:
            raise
        except Exception as exc:
            # Attempt OCR fallback for any parser failure
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_file_extraction.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/file_extraction.py backend/app/tests/test_file_extraction.py
git commit -m "feat: add FileExtractionService with parser dispatch and OCR fallback"
```

---

### Task 7: Add temp file helpers to storage module

**Files:**
- Modify: `backend/app/storage/__init__.py`

- [ ] **Step 1: Update `storage/__init__.py`**

Replace the current content with:

```python
"""临时文件管理 —— 文件提取后即清理，不持久化。

提供临时文件写入和清理辅助函数，供 FileExtractionService 使用。
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

TEMP_ROOT = Path("/tmp/lexad")


def save_upload_temp(upload_file) -> Path:
    """Write an uploaded file to a temp directory, return the path."""
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    session_dir = TEMP_ROOT / str(uuid.uuid4())
    session_dir.mkdir(parents=True, exist_ok=True)

    file_path = session_dir / (upload_file.filename or "upload")
    with open(file_path, "wb") as f:
        f.write(upload_file.file.read())
    return file_path


def cleanup_temp(file_path: str | Path) -> None:
    """Remove the temp directory containing the given file."""
    path = Path(file_path)
    if path.parent.parent == TEMP_ROOT:
        shutil.rmtree(path.parent, ignore_errors=True)
```

- [ ] **Step 2: Verify the module imports cleanly**

Run: `cd backend && python -c "from app.storage import save_upload_temp, cleanup_temp; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/storage/__init__.py
git commit -m "feat: add temp file helpers for upload extraction pipeline"
```

---

### Task 8: Update MaterialSubmit schema

**Files:**
- Modify: `backend/app/schemas/material.py`

- [ ] **Step 1: Update `MaterialSubmit` schema**

Replace the `MaterialSubmit` class in `backend/app/schemas/material.py`:

```python
class MaterialSubmit(BaseModel):
    name: str = Field(..., max_length=200)
    industry: str = Field(default="", max_length=50)
    platforms: list[str] = Field(default_factory=list)
    material_type: str = Field(default="文字")
    raw_text: str = Field(default="")  # 改为可选，允许纯文件提交
    priority: str = Field(default="normal", pattern="^(normal|urgent|extreme)$")
    deadline: datetime | None = None
```

(The only change is `raw_text: str` → `raw_text: str = Field(default="")`)

- [ ] **Step 2: Add preview response schema**

Append to `backend/app/schemas/material.py`:

```python
class PreviewTextResponse(BaseModel):
    text: str
    quality: str
    source_format: str
```

- [ ] **Step 3: Verify the schema imports cleanly**

Run: `cd backend && python -c "from app.schemas.material import MaterialSubmit, PreviewTextResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/material.py
git commit -m "feat: make raw_text optional in MaterialSubmit, add PreviewTextResponse schema"
```

---

### Task 9: Update MaterialService to integrate file extraction

**Files:**
- Modify: `backend/app/services/material_service.py`

- [ ] **Step 1: Update `create_material` to accept optional extracted text**

Replace the `create_material` function in `backend/app/services/material_service.py`:

```python
def create_material(
    db: Session,
    data: MaterialSubmit,
    submitter_id: str,
    extracted_text: str = "",
) -> Material:
    final_text = _merge_texts(extracted_text, data.raw_text)
    material = Material(
        name=data.name,
        industry=data.industry,
        platforms=data.platforms,
        material_type=data.material_type,
        raw_text=final_text,
        priority=data.priority,
        deadline=data.deadline,
        status=MaterialStatus.draft,
        submitter_id=submitter_id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def _merge_texts(extracted: str, form_text: str) -> str:
    parts = [t.strip() for t in (extracted, form_text) if t.strip()]
    return "\n".join(parts)
```

- [ ] **Step 2: Verify imports**

Run: `cd backend && python -c "from app.services.material_service import create_material, _merge_texts; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/material_service.py
git commit -m "feat: integrate file extraction text into material creation flow"
```

---

### Task 10: Update materials endpoint (multipart submit + preview-text)

**Files:**
- Modify: `backend/app/api/v1/endpoints/materials.py`

- [ ] **Step 1: Rewrite the materials endpoint**

Replace the entire content of `backend/app/api/v1/endpoints/materials.py`:

```python
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.material import MaterialSubmit, MaterialUpdate, MaterialOut, MaterialListItem, PreviewTextResponse
from app.services import material_service
from app.services.file_extraction import FileExtractionService, ExtractionError
from app.storage import save_upload_temp, cleanup_temp

router = APIRouter()
_extraction_svc = FileExtractionService()

SUPPORTED_FORMATS = "JPG/PNG/GIF/BMP/PDF/DOCX/DOC/PPTX/XLSX/TXT"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/submit", response_model=MaterialOut, status_code=201)
async def submit_material(
    body: str = Form(...),
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = MaterialSubmit(**json.loads(body))
    extracted_text = ""
    extraction_meta = None

    if file and file.filename:
        _validate_file(file)
        tmp_path = None
        try:
            mime = _extraction_svc.mime_from_extension(file.filename)
            if not _extraction_svc.is_supported(mime):
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件格式，支持：{SUPPORTED_FORMATS}",
                )
            tmp_path = save_upload_temp(file)
            result = _extraction_svc.extract(tmp_path, mime)
            extracted_text = result.text
            extraction_meta = {
                "source_format": result.source_format,
                "quality": result.quality,
                "fallback_used": result.fallback_used,
            }
        except ExtractionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            if tmp_path:
                cleanup_temp(tmp_path)

    if not extracted_text.strip() and not data.raw_text.strip():
        raise HTTPException(
            status_code=400,
            detail="请提供广告文案内容或上传文件",
        )

    material = material_service.create_material(db, data, user.id, extracted_text)
    return material


@router.post("/preview-text", response_model=PreviewTextResponse)
async def preview_text(
    file: UploadFile = File(...),
):
    _validate_file(file)
    mime = _extraction_svc.mime_from_extension(file.filename)
    if not _extraction_svc.is_supported(mime):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，支持：{SUPPORTED_FORMATS}",
        )

    tmp_path = None
    try:
        tmp_path = save_upload_temp(file)
        result = _extraction_svc.extract(tmp_path, mime)
        return PreviewTextResponse(
            text=result.text,
            quality=result.quality,
            source_format=result.source_format,
        )
    except ExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if tmp_path:
            cleanup_temp(tmp_path)


def _validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")
    # Read into memory to check size — UploadFile may not have size attr
    content = file.file.read()
    file.file.seek(0)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="文件过大（上限 10MB），请压缩后重试",
        )


@router.get("/list", response_model=list[MaterialListItem])
def list_materials(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return material_service.list_materials(db, user)


@router.get("/{material_id}", response_model=MaterialOut)
def get_material(material_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = material_service.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@router.put("/{material_id}", response_model=MaterialOut)
def update_material(material_id: str, body: MaterialUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = material_service.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material.submitter_id != user.id:
        raise HTTPException(status_code=403, detail="Not your material")
    if material.status.value not in ("draft", "returned"):
        raise HTTPException(status_code=400, detail="Can only edit draft or returned materials")
    return material_service.update_material(db, material_id, body)


@router.get("/{material_id}/versions")
def get_versions(material_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"versions": material_service.get_material_versions(db, material_id)}
```

- [ ] **Step 2: Verify the endpoint module imports cleanly**

Run: `cd backend && python -c "from app.api.v1.endpoints.materials import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/endpoints/materials.py
git commit -m "feat: convert materials submit to async multipart, add preview-text endpoint"
```

---

### Task 11: Update extract_meta recording in review

**Files:**
- Modify: `backend/app/services/review_service.py`

- [ ] **Step 1: Optionally pass extraction_meta to review result**

The `trigger_ai_review` already saves `engine_result.model_dump()` to `ai_result`. If we want extraction metadata recorded, we can inject it into the engine result. For now, since the engine only needs `raw_text`, this is optional. Skip this task unless you want extraction metadata in the review record.

**Decision: Skip for MVP** — extraction metadata is available in the response at submit time only.

---

### Task 12: Update frontend types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add preview response type**

Append to `frontend/src/types/index.ts`:

```typescript
export interface PreviewTextResponse {
  text: string
  quality: 'good' | 'degraded' | 'minimal'
  source_format: string
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add PreviewTextResponse type"
```

---

### Task 13: Update frontend materials API

**Files:**
- Modify: `frontend/src/api/materials.ts`

- [ ] **Step 1: Rewrite `materials.ts` for FormData + previewText**

Replace the content of `frontend/src/api/materials.ts`:

```typescript
import client from './client'
import type { Material, PreviewTextResponse } from '@/types'

export const materialsApi = {
  submit: (formData: FormData) =>
    client.post<Material>('/materials/submit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  previewText: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post<PreviewTextResponse>('/materials/preview-text', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: () => client.get<Material[]>('/materials/list'),
  get: (id: string) => client.get<Material>(`/materials/${id}`),
  update: (id: string, data: Record<string, any>) =>
    client.put<Material>(`/materials/${id}`, data),
  versions: (id: string) =>
    client.get<{ versions: any[] }>(`/materials/${id}/versions`),
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/materials.ts
git commit -m "feat: update materials API for FormData submission and add previewText"
```

---

### Task 14: Update SubmitPage with file upload and preview

**Files:**
- Modify: `frontend/src/pages/SubmitPage.vue`

- [ ] **Step 1: Rewrite `SubmitPage.vue`**

Replace the content of `frontend/src/pages/SubmitPage.vue`:

```vue
<!-- frontend/src/pages/SubmitPage.vue -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const router = useRouter()
const MAX_FILE_SIZE = 10 * 1024 * 1024

const form = ref({
  name: '',
  industry: '',
  platforms: [] as string[],
  material_type: '文字',
  raw_text: '',
  priority: 'normal',
  deadline: null as string | null,
})

const industries = ['食品', '医疗', '教育', '汽车', '金融', '美妆', '直播电商']
const platforms = ['抖音', '小红书', '微信', '微博', '京东', '淘宝']
const materialTypes = ['文字', '图片', 'PDF文档', 'Word文档', 'PPT演示', 'Excel表格', '视频脚本', '直播话术']
const submitting = ref(false)
const error = ref('')

const selectedFile = ref<File | null>(null)
const extractedText = ref('')
const previewQuality = ref<'good' | 'degraded' | 'minimal' | null>(null)
const previewing = ref(false)
const isDragOver = ref(false)

const allowedExtensions = '.jpg,.jpeg,.png,.gif,.bmp,.pdf,.docx,.doc,.pptx,.xlsx,.txt'

function fileSizeDisplay(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function guessMaterialType(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    jpg: '图片', jpeg: '图片', png: '图片', gif: '图片', bmp: '图片',
    pdf: 'PDF文档',
    docx: 'Word文档', doc: 'Word文档',
    pptx: 'PPT演示',
    xlsx: 'Excel表格',
    txt: '文字',
  }
  return map[ext] ?? '文字'
}

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) setFile(input.files[0])
  input.value = ''
}

function handleDrop(e: DragEvent) {
  isDragOver.value = false
  if (e.dataTransfer?.files?.[0]) setFile(e.dataTransfer.files[0])
}

function setFile(file: File) {
  const ext = '.' + (file.name.split('.').pop()?.toLowerCase() ?? '')
  if (!allowedExtensions.includes(ext)) {
    error.value = '不支持的文件格式，支持：JPG/PNG/PDF/DOCX/DOC/PPTX/XLSX/TXT'
    return
  }
  if (file.size > MAX_FILE_SIZE) {
    error.value = '文件过大（上限 10MB），请压缩后重试'
    return
  }
  error.value = ''
  selectedFile.value = file
  extractedText.value = ''
  previewQuality.value = null
  form.value.material_type = guessMaterialType(file.name)
}

function removeFile() {
  selectedFile.value = null
  extractedText.value = ''
  previewQuality.value = null
}

async function handlePreview() {
  if (!selectedFile.value) return
  previewing.value = true
  error.value = ''
  try {
    const res = await materialsApi.previewText(selectedFile.value)
    extractedText.value = res.data.text
    previewQuality.value = res.data.quality
  } catch (e: any) {
    error.value = e.response?.data?.detail || '文本提取失败'
  } finally {
    previewing.value = false
  }
}

const qualityLabel = computed(() => {
  if (previewQuality.value === 'good') return { text: '识别质量：良好', cls: 'text-green-600' }
  if (previewQuality.value === 'degraded') return { text: '识别质量：一般（已使用降级方案）', cls: 'text-yellow-600' }
  if (previewQuality.value === 'minimal') return { text: '识别质量：较低，建议人工核对', cls: 'text-red-500' }
  return null
})

const finalText = computed({
  get: () => extractedText.value || form.value.raw_text,
  set: (val: string) => {
    if (selectedFile.value) {
      extractedText.value = val
    } else {
      form.value.raw_text = val
    }
  },
})

async function handleSubmit() {
  error.value = ''
  submitting.value = true

  const fd = new FormData()
  const body = JSON.stringify({
    ...form.value,
    raw_text: finalText.value,
    deadline: form.value.deadline || undefined,
  })
  fd.append('body', body)
  if (selectedFile.value) {
    fd.append('file', selectedFile.value)
  }

  try {
    const res = await materialsApi.submit(fd)
    const reviewRes = await reviewsApi.aiReview(res.data.id)
    router.push(`/result/${reviewRes.data.id}`)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '提交失败'
  } finally {
    submitting.value = false
  }
}

function togglePlatform(p: string) {
  const idx = form.value.platforms.indexOf(p)
  if (idx >= 0) form.value.platforms.splice(idx, 1)
  else form.value.platforms.push(p)
}
</script>

<template>
  <DefaultLayout>
    <div class="max-w-2xl mx-auto p-8">
      <h2 class="text-xl font-bold mb-6">提交广告物料</h2>
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div>
          <label class="block text-sm font-medium mb-1">物料名称 *</label>
          <input v-model="form.name" class="input" required placeholder="如：诺优能益生菌春节推广文案" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">行业类型</label>
            <select v-model="form.industry" class="input">
              <option value="">请选择</option>
              <option v-for="ind in industries" :key="ind" :value="ind">{{ ind }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">物料类型</label>
            <select v-model="form.material_type" class="input">
              <option v-for="mt in materialTypes" :key="mt" :value="mt">{{ mt }}</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">投放平台</label>
          <div class="flex flex-wrap gap-2">
            <button type="button" v-for="p in platforms" :key="p"
              @click="togglePlatform(p)"
              :class="form.platforms.includes(p) ? 'btn-primary text-sm' : 'btn-outline text-sm'">
              {{ p }}
            </button>
          </div>
        </div>

        <!-- File upload area -->
        <div>
          <label class="block text-sm font-medium mb-1">上传文件（可选）</label>
          <div
            class="border-2 border-dashed rounded-lg p-6 text-center transition-colors"
            :class="isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300'"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleDrop"
          >
            <template v-if="!selectedFile">
              <p class="text-gray-500 mb-2">拖拽文件到此处 或 点击选择</p>
              <p class="text-gray-400 text-xs">
                支持 JPG / PNG / GIF / BMP / PDF / DOCX / DOC / PPTX / XLSX / TXT，单文件最大 10MB
              </p>
              <input
                type="file"
                :accept="allowedExtensions"
                class="mt-3 text-sm"
                @change="handleFileSelect"
              />
            </template>
            <template v-else>
              <div class="flex items-center justify-center gap-3">
                <span class="text-sm font-medium">{{ selectedFile.name }}</span>
                <span class="text-xs text-gray-500">({{ fileSizeDisplay(selectedFile.size) }})</span>
              </div>
              <div class="flex items-center justify-center gap-3 mt-3">
                <button type="button" class="btn-outline text-sm" :disabled="previewing" @click="handlePreview">
                  {{ previewing ? '提取中...' : '预览提取文本' }}
                </button>
                <button type="button" class="text-sm text-red-500 hover:underline" @click="removeFile">
                  移除
                </button>
              </div>
            </template>
          </div>
        </div>

        <!-- Text content: with quality label if file was processed -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="text-sm font-medium">广告文案内容 *</label>
            <span v-if="qualityLabel" :class="qualityLabel.cls" class="text-xs">{{ qualityLabel.text }}</span>
          </div>
          <textarea
            v-model="finalText"
            class="input h-40 resize-y"
            required
            :placeholder="selectedFile ? '预览提取的文本，可编辑修改' : '粘贴广告文案全文...'"
          ></textarea>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">优先级</label>
            <select v-model="form.priority" class="input">
              <option value="normal">普通</option>
              <option value="urgent">加急 (24h)</option>
              <option value="extreme">极速 (4h)</option>
            </select>
          </div>
          <div v-if="form.priority !== 'normal'">
            <label class="block text-sm font-medium mb-1">截止时间</label>
            <input v-model="form.deadline" type="datetime-local" class="input" />
          </div>
        </div>
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="submitting" class="btn-primary w-full">
          {{ submitting ? '提交并审查中...' : '提交并开始AI审查' }}
        </button>
      </form>
    </div>
  </DefaultLayout>
</template>
```

- [ ] **Step 2: Run frontend dev server and verify it compiles**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SubmitPage.vue
git commit -m "feat: add file upload, preview, and in-place editing to SubmitPage"
```

---

### Task 15: Run full test suite and integration verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest app/tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run backend server and verify endpoints manually**

Run: `cd backend && uvicorn app.main:app --reload --port 8000`

Then test with curl (or PowerShell equivalent):

```bash
# Test preview-text with a text file
echo "测试广告文案内容" > /tmp/test_ad.txt
curl -X POST http://localhost:8000/api/v1/materials/preview-text \
  -F "file=@/tmp/test_ad.txt"

# Expected: {"text":"测试广告文案内容","quality":"good","source_format":"txt_raw"}
```

- [ ] **Step 3: Commit any final cleanup**

```bash
git status
# Verify all changes are committed
```

---

## Completion Checklist

- [ ] All parsers created and tested
- [ ] FileExtractionService dispatches to correct parser
- [ ] Submit endpoint accepts multipart with optional file
- [ ] Preview-text endpoint extracts without saving
- [ ] Empty submission (no text + no file) returns 400
- [ ] Unsupported format returns 400 with supported list
- [ ] File >10MB returns 413
- [ ] Frontend SubmitPage has file drop zone + preview + edit
- [ ] Full end-to-end submit → review flow works with a file
