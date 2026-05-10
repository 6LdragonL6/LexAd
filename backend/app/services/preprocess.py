"""Preprocess service: handles text + optional image."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.schemas.models import PreprocessResult
from app.utils.file_handler import validate_image_extension
from app.utils.ocr import extract_ocr_text


def run_preprocess(raw_text: str, image_file: UploadFile | None = None) -> PreprocessResult:
    warnings: list[str] = []
    ocr_text = ""
    image_summary = ""

    if not raw_text.strip():
        warnings.append("输入文本为空，请补充广告文案内容。")

    if image_file is not None and image_file.filename:
        if not validate_image_extension(image_file.filename):
            warnings.append(
                f"不支持的文件格式: {Path(image_file.filename).suffix}。"
                f"支持的格式: PNG, JPG, JPEG, BMP, TIFF, WebP。"
            )
            image_summary = f"Invalid file format: {image_file.filename}"
            return PreprocessResult(
                ocr_text="",
                image_summary=image_summary,
                preprocess_status="warning",
                warnings=warnings,
            )

        try:
            suffix = Path(image_file.filename).suffix or ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                content = image_file.file.read()
                tmp.write(content)
                temp_path = tmp.name
            ocr_result = extract_ocr_text(temp_path)
            ocr_text = ocr_result.text
            image_summary = f"Image received: {image_file.filename}"
            if ocr_result.status == "mock":
                warnings.append("Tesseract 未安装，OCR 返回占位结果。")
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            warnings.append("图片处理失败，继续使用空 OCR 结果。")
            ocr_text = ""
            image_summary = f"Image upload attempted but processing failed: {image_file.filename}"
    else:
        image_summary = "No image uploaded."

    return PreprocessResult(
        ocr_text=ocr_text,
        image_summary=image_summary,
        preprocess_status="ok" if not warnings else "warning",
        warnings=warnings,
    )
