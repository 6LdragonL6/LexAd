"""广告审查端点 —— 提交审查、获取结果、查询案例库和模板库。"""

from __future__ import annotations

from fastapi import APIRouter, Form, UploadFile

from app.core.config import DATA_DIR
from app.schemas.models import StandardResponse
from app.services.pipeline import run_full_pipeline
from app.utils.json_reader import read_json_list

router = APIRouter()

# 内存存储（仅用于 Demo，重启后清空）
_result_store: dict[str, StandardResponse] = {}


@router.post("/submit", response_model=StandardResponse)
async def review_submit(
    raw_text: str = Form(default=""),
    image_file: UploadFile | None = None,
):
    """提交广告内容进行合规审查，返回包含三层审查的完整结果。"""
    result = run_full_pipeline(raw_text, image_file)
    _result_store[result.request_id] = result
    return result


@router.get("/result/{request_id}", response_model=StandardResponse)
async def review_result(request_id: str):
    """根据请求 ID 查询广告合规审查结果。"""
    from app.core.exceptions import NotFoundError
    result = _result_store.get(request_id)
    if result is None:
        raise NotFoundError(detail=f"Review result not found: {request_id}")
    return result


@router.get("/cases")
async def list_cases():
    """获取案例库列表，返回所有历史违规案例条目。"""
    cases = read_json_list(DATA_DIR / "case_library.json")
    return {"items": cases, "total": len(cases)}


@router.get("/templates")
async def list_templates():
    """获取改写模板库列表，返回所有广告文案合规改写模板。"""
    templates = read_json_list(DATA_DIR / "rewrite_templates.json")
    return {"items": templates, "total": len(templates)}
