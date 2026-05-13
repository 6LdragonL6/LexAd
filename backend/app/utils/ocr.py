"""OCR 工具 —— 基于 Tesseract 的真实 OCR 识别，不可用时自动回退 Mock。"""

import logging
import os
from pathlib import Path

from app.core.config import DATA_DIR, get_settings
from app.schemas.models import OCRResult

settings = get_settings()
logger = logging.getLogger(__name__)

# Tesseract 可执行文件路径（Windows 默认安装位置）
_TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# 项目本地语言包目录（存放额外下载的 .traineddata 文件）
_TESSDATA_DIR = DATA_DIR.parent / "tessdata"


def _configure_tesseract() -> str | None:
    """查找 Tesseract 并配置 pytesseract，返回可执行文件路径或 None。"""
    tesseract_path = None

    # 优先检查 Windows 默认路径
    if Path(_TESSERACT_EXE).exists():
        tesseract_path = _TESSERACT_EXE
    else:
        # 回退到 PATH 查找
        import shutil
        found = shutil.which("tesseract")
        if found:
            tesseract_path = found

    if tesseract_path is None:
        return None

    # 设置 pytesseract 的 tesseract 路径
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    except ImportError:
        logger.warning("pytesseract 未安装，将使用 subprocess 回退模式。")

    # 配置 tessdata 路径（优先使用项目本地 tessdata 目录）
    if _TESSDATA_DIR.exists() and any(_TESSDATA_DIR.iterdir()):
        os.environ.setdefault("TESSDATA_PREFIX", str(_TESSDATA_DIR))

    return tesseract_path


def _do_ocr_pytesseract(image_path: str, lang: str = "chi_sim+eng") -> OCRResult:
    """使用 pytesseract 执行 OCR 识别并获取置信度。"""
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=lang).strip()

        # 获取逐词置信度
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
        confidences = [int(c) for c in data["conf"] if c != "-1"]
        avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

        if not text:
            return OCRResult(
                text="",
                status="ok",
                provider="tesseract",
                confidence=avg_confidence,
                error_message="图片中未识别到文字。",
            )

        return OCRResult(
            text=text,
            status="ok",
            provider="tesseract",
            confidence=min(avg_confidence, 1.0),
            error_message="",
        )

    except ImportError:
        logger.warning("pytesseract 不可用，回退 subprocess 模式。")
        return _do_ocr_subprocess(image_path, lang)
    except Exception as e:
        logger.exception("pytesseract OCR 异常")
        return OCRResult(
            text="",
            status="error",
            provider="tesseract",
            confidence=0.0,
            error_message=f"OCR 识别异常: {str(e)}",
        )


def _do_ocr_subprocess(image_path: str, lang: str = "chi_sim+eng") -> OCRResult:
    """使用 subprocess 调用 Tesseract 命令行（无 pytesseract 时的回退方案）。"""
    import subprocess

    tesseract_path = _TESSERACT_EXE if Path(_TESSERACT_EXE).exists() else "tesseract"

    try:
        result = subprocess.run(
            [tesseract_path, image_path, "stdout", "-l", lang, "--psm", "6"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        text = result.stdout.strip()

        if result.returncode != 0 and not text:
            return OCRResult(
                text="",
                status="error",
                provider="tesseract",
                confidence=0.0,
                error_message=f"Tesseract 执行失败: {result.stderr.strip()}",
            )

        if not text:
            return OCRResult(
                text="",
                status="ok",
                provider="tesseract",
                confidence=0.0,
                error_message="图片中未识别到文字。",
            )

        return OCRResult(
            text=text,
            status="ok",
            provider="tesseract",
            confidence=0.0,
            error_message="",
        )

    except subprocess.TimeoutExpired:
        return OCRResult(
            text="",
            status="error",
            provider="tesseract",
            confidence=0.0,
            error_message="OCR 识别超时。",
        )
    except Exception as e:
        logger.exception("subprocess OCR 异常")
        return OCRResult(
            text="",
            status="error",
            provider="tesseract",
            confidence=0.0,
            error_message=f"OCR 识别异常: {str(e)}",
        )


def extract_ocr_text(image_path: str) -> OCRResult:
    """从图片中提取 OCR 文本，优先使用真实 Tesseract，不可用时回退 Mock。"""
    path = Path(image_path)

    if not path.exists():
        return OCRResult(
            text="",
            status="image_missing",
            provider="tesseract_mock",
            confidence=0.0,
            error_message=f"图片文件不存在: {image_path}",
        )

    # 尝试真实 OCR
    if settings.TESSERACT_AVAILABLE:
        tesseract_ok = _configure_tesseract()
        if tesseract_ok:
            return _do_ocr_pytesseract(image_path, lang="chi_sim+eng")

    # 回退 Mock
    return OCRResult(
        text="[OCR mock] Tesseract 未安装或未启用，返回占位结果。",
        status="mock",
        provider="tesseract_mock",
        confidence=0.0,
        error_message="",
    )
