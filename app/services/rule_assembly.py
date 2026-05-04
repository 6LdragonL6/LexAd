"""Rule assembly service: builds the standardized request body from raw inputs.

Does NOT perform real rule evaluation — only assembles structured JSON.
"""

from __future__ import annotations

from app.schemas.models import (
    ImageMeta,
    PreprocessResult,
    StandardInput,
    StandardRequest,
)
from app.utils.id_gen import generate_request_id, utc_now_iso


def assemble_standard_request(
    raw_text: str,
    image_filename: str | None,
    preprocess_result: PreprocessResult,
) -> StandardRequest:
    """Assemble a StandardRequest from raw input and preprocess results.

    Args:
        raw_text: Raw advertising text.
        image_filename: Uploaded image filename, if any.
        preprocess_result: Result from the preprocess service.

    Returns:
        StandardRequest ready for the review pipeline.
    """
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
