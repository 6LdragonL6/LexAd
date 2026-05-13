"""LexAd 广告合规审查平台的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── 输入 / 表单 ────────────────────────────────────────────────────────────

class ReviewFormInput(BaseModel):
    """用户提交的审查表单输入（前端表单字段）。"""
    raw_text: str = Field(default="", description="原始广告文案文本")
    image_filename: Optional[str] = Field(default=None, description="上传的图片文件名（如有）")


class ImageMeta(BaseModel):
    """上传图片的元信息。"""
    filename: str = ""
    size_bytes: int = 0
    content_type: str = ""
    status: str = "no_image"


class OCRResult(BaseModel):
    """OCR 识别结果。"""
    text: str = ""
    status: str = "ok"
    provider: str = "tesseract_mock"
    confidence: float = 0.0
    error_message: str = ""


class PreprocessResult(BaseModel):
    """预处理结果：包含 OCR 文本、图片摘要和警告信息。"""
    ocr_text: str = ""
    image_summary: str = ""
    preprocess_status: str = "ok"
    warnings: list[str] = Field(default_factory=list)


# ── 规则 ───────────────────────────────────────────────────────────────────

class MatchedRule(BaseModel):
    """命中的合规规则信息。"""
    rule_id: str = ""
    rule_text: str = ""
    source: str = ""
    match_type: str = "keyword"


# ── 审查层级 ───────────────────────────────────────────────────────────────

class SingleLayerReview(BaseModel):
    """单层审查结果（法律 / 行业 / 平台其中之一）。"""
    level: str = ""
    status: str = "pending"
    risk_score: int = 0
    matched_rules: list[MatchedRule] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ThreeLayerReview(BaseModel):
    """三层审查汇总结果：法律层面 + 行业层面 + 平台层面。"""
    legal_review: SingleLayerReview = Field(default_factory=SingleLayerReview)
    industry_review: SingleLayerReview = Field(default_factory=SingleLayerReview)
    platform_review: SingleLayerReview = Field(default_factory=SingleLayerReview)


# ── 案例与模板 ─────────────────────────────────────────────────────────────

class CaseReference(BaseModel):
    """匹配到的历史案例参考。"""
    case_id: str = ""
    title: str = ""
    similarity: float = 0.0
    relevance: str = ""
    summary: str = ""


class RewriteTemplate(BaseModel):
    """广告文案合规改写模板。"""
    template_id: str = ""
    title: str = ""
    before: str = ""
    after: str = ""
    note: str = ""


# ── 罚金评估 ───────────────────────────────────────────────────────────────

class PenaltyAssessment(BaseModel):
    """罚金评估结果。"""
    penalty_level: str = "none"
    penalty_amount: str = "0"
    assessment_notes: str = ""


# ── 最终结论 ───────────────────────────────────────────────────────────────

class FinalResult(BaseModel):
    """审查最终结论：综合状态、总结、建议和备注。"""
    overall_status: str = "pending"
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)
    notes: str = ""


# ── 标准化请求 / 响应 ──────────────────────────────────────────────────────

class StandardInput(BaseModel):
    """标准化输入：原始文本 + 图片元信息。"""
    raw_text: str = ""
    image_meta: ImageMeta = Field(default_factory=ImageMeta)


class StandardRequest(BaseModel):
    """标准化审查请求体：包含输入和预处理结果。"""
    request_id: str = ""
    created_at: str = ""
    input: StandardInput = Field(default_factory=StandardInput)
    preprocess: PreprocessResult = Field(default_factory=PreprocessResult)


class StandardResponse(BaseModel):
    """标准化审查响应体：包含审查全流程的所有环节结果。"""
    request_id: str = ""
    created_at: str = ""
    input: StandardInput = Field(default_factory=StandardInput)
    preprocess: PreprocessResult = Field(default_factory=PreprocessResult)
    review: ThreeLayerReview = Field(default_factory=ThreeLayerReview)
    case_references: list[CaseReference] = Field(default_factory=list)
    rewrite_templates: list[RewriteTemplate] = Field(default_factory=list)
    penalty_assessment: PenaltyAssessment = Field(default_factory=PenaltyAssessment)
    final_result: FinalResult = Field(default_factory=FinalResult)
