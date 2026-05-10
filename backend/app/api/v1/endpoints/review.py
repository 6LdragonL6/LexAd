"""Review endpoints — advertising compliance review API."""

from __future__ import annotations

from fastapi import APIRouter, Form, UploadFile

from app.core.config import DATA_DIR
from app.schemas.models import StandardResponse
from app.services.pipeline import run_full_pipeline
from app.utils.json_reader import read_json_list

router = APIRouter()

# In-memory store for demo purposes (resets on restart)
_result_store: dict[str, StandardResponse] = {}


@router.post("/submit", response_model=StandardResponse)
async def review_submit(
    raw_text: str = Form(default=""),
    image_file: UploadFile | None = None,
):
    """Submit advertising content for compliance review."""
    result = run_full_pipeline(raw_text, image_file)
    _result_store[result.request_id] = result
    return result


@router.get("/result/{request_id}", response_model=StandardResponse)
async def review_result(request_id: str):
    """Get review result by request ID."""
    from app.core.exceptions import NotFoundError
    result = _result_store.get(request_id)
    if result is None:
        raise NotFoundError(detail=f"Review result not found: {request_id}")
    return result


@router.get("/cases")
async def list_cases():
    """Get case library entries."""
    cases = read_json_list(DATA_DIR / "case_library.json")
    return {"items": cases, "total": len(cases)}


@router.get("/templates")
async def list_templates():
    """Get rewrite template library entries."""
    templates = read_json_list(DATA_DIR / "rewrite_templates.json")
    return {"items": templates, "total": len(templates)}
