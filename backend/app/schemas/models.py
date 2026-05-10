"""Pydantic models for LexAd advertising compliance review platform."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Input / Form ────────────────────────────────────────────────────────────

class ReviewFormInput(BaseModel):
    raw_text: str = Field(default="", description="Raw advertising text input")
    image_filename: Optional[str] = Field(default=None, description="Uploaded image filename, if any")


class ImageMeta(BaseModel):
    filename: str = ""
    size_bytes: int = 0
    content_type: str = ""
    status: str = "no_image"


class OCRResult(BaseModel):
    text: str = ""
    status: str = "ok"
    provider: str = "tesseract_mock"
    confidence: float = 0.0
    error_message: str = ""


class PreprocessResult(BaseModel):
    ocr_text: str = ""
    image_summary: str = ""
    preprocess_status: str = "ok"
    warnings: list[str] = Field(default_factory=list)


# ── Rules ───────────────────────────────────────────────────────────────────

class MatchedRule(BaseModel):
    rule_id: str = ""
    rule_text: str = ""
    source: str = ""
    match_type: str = "keyword"


# ── Review Layers ───────────────────────────────────────────────────────────

class SingleLayerReview(BaseModel):
    level: str = ""
    status: str = "pending"
    risk_score: int = 0
    matched_rules: list[MatchedRule] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ThreeLayerReview(BaseModel):
    legal_review: SingleLayerReview = Field(default_factory=SingleLayerReview)
    industry_review: SingleLayerReview = Field(default_factory=SingleLayerReview)
    platform_review: SingleLayerReview = Field(default_factory=SingleLayerReview)


# ── Cases & Templates ──────────────────────────────────────────────────────

class CaseReference(BaseModel):
    case_id: str = ""
    title: str = ""
    similarity: float = 0.0
    relevance: str = ""
    summary: str = ""


class RewriteTemplate(BaseModel):
    template_id: str = ""
    title: str = ""
    before: str = ""
    after: str = ""
    note: str = ""


# ── Penalty Assessment ─────────────────────────────────────────────────────

class PenaltyAssessment(BaseModel):
    penalty_level: str = "none"
    penalty_amount: str = "0"
    assessment_notes: str = ""


# ── Final Result ────────────────────────────────────────────────────────────

class FinalResult(BaseModel):
    overall_status: str = "pending"
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)
    notes: str = ""


# ── Standardized Request / Response ─────────────────────────────────────────

class StandardInput(BaseModel):
    raw_text: str = ""
    image_meta: ImageMeta = Field(default_factory=ImageMeta)


class StandardRequest(BaseModel):
    request_id: str = ""
    created_at: str = ""
    input: StandardInput = Field(default_factory=StandardInput)
    preprocess: PreprocessResult = Field(default_factory=PreprocessResult)


class StandardResponse(BaseModel):
    request_id: str = ""
    created_at: str = ""
    input: StandardInput = Field(default_factory=StandardInput)
    preprocess: PreprocessResult = Field(default_factory=PreprocessResult)
    review: ThreeLayerReview = Field(default_factory=ThreeLayerReview)
    case_references: list[CaseReference] = Field(default_factory=list)
    rewrite_templates: list[RewriteTemplate] = Field(default_factory=list)
    penalty_assessment: PenaltyAssessment = Field(default_factory=PenaltyAssessment)
    final_result: FinalResult = Field(default_factory=FinalResult)
