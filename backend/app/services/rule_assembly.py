"""规则组装服务 —— 将原始输入构建为标准化审查请求。"""

from __future__ import annotations

from app.schemas.models import ImageMeta, PreprocessResult, StandardInput, StandardRequest
from app.utils.id_gen import generate_request_id, utc_now_iso


def assemble_standard_request(
    raw_text: str,
    image_filename: str | None,
    preprocess_result: PreprocessResult,
) -> StandardRequest:
    """将原始文本、图片信息和预处理结果组装为带唯一请求 ID 和时间戳的 StandardRequest。"""
    return StandardRequest(
        request_id=generate_request_id(),
        created_at=utc_now_iso(),
        input=StandardInput(
            raw_text=raw_text,
            image_meta=ImageMeta(
                filename=image_filename or "",
                status="has_image" if image_filename else "no_image",
            ),
        ),
        preprocess=preprocess_result,
    )
