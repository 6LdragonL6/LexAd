"""Pydantic models for LexAd advertising compliance review platform.

All core data structures are explicitly defined here.
Field types are explicit, defaults are reasonable, and models are designed for easy extension.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Input / Form ────────────────────────────────────────────────────────────

class ReviewFormInput(BaseModel):
    """Form input from the review page."""
    raw_text: str = Field(default="", description="Raw advertising text input")
    image_filename: Optional[str] = Field(default=None, description="Uploaded image filename, if any")


class ImageMeta(BaseModel):
    """Metadata about an uploaded image."""
    filename: str = ""
    size_bytes: int = 0
    content_type: str = ""
    status: str = "no_image"


class OCRResult(BaseModel):
    """Result from OCR processing (local Tesseract placeholder)."""
    text: str = ""
    status: str = "ok"
    provider: str = "tesseract_mock"
    confidence: float = 0.0
    error_message: str = ""


class PreprocessResult(BaseModel):
    """Output of the preprocess service."""
    ocr_text: str = ""
    image_summary: str = ""
    preprocess_status: str = "ok"
    warnings: list[str] = Field(default_factory=list)


# ── Rules ───────────────────────────────────────────────────────────────────

class MatchedRule(BaseModel):
    """A single matched rule reference."""
    rule_id: str = ""
    rule_text: str = ""
    source: str = ""
    match_type: str = "keyword"


# ── Review Layers ───────────────────────────────────────────────────────────

class SingleLayerReview(BaseModel):
    """One layer of compliance review (legal / industry / platform)."""
    level: str = ""
    status: str = "pending"
    risk_score: int = 0
    matched_rules: list[MatchedRule] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ThreeLayerReview(BaseModel):
    """All three review layers combined."""
    legal_review: SingleLayerReview = Field(default_factory=SingleLayerReview)
    industry_review: SingleLayerReview = Field(default_factory=SingleLayerReview)
    platform_review: SingleLayerReview = Field(default_factory=SingleLayerReview)


# ── Cases & Templates ──────────────────────────────────────────────────────

class CaseReference(BaseModel):
    """A single case reference from the case library."""
    case_id: str = ""
    title: str = ""
    similarity: float = 0.0
    relevance: str = ""
    summary: str = ""


class RewriteTemplate(BaseModel):
    """A single rewrite template suggestion."""
    template_id: str = ""
    title: str = ""
    before: str = ""
    after: str = ""
    note: str = ""


# ── Penalty Assessment ─────────────────────────────────────────────────────

class PenaltyAssessment(BaseModel):
    """Penalty assessment mock result."""
    penalty_level: str = "none"
    penalty_amount: str = "0"
    assessment_notes: str = ""


# ── Final Result ────────────────────────────────────────────────────────────

class FinalResult(BaseModel):
    """Final suggestion generated from all review layers and analysis."""
    overall_status: str = "pending"
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)
    notes: str = ""


# ── Standardized Request / Response ─────────────────────────────────────────

class StandardInput(BaseModel):
    """Standardized input section of the review request."""
    raw_text: str = ""
    image_meta: ImageMeta = Field(default_factory=ImageMeta)


class StandardRequest(BaseModel):
    """Full standardized review request body."""
    request_id: str = ""
    created_at: str = ""
    input: StandardInput = Field(default_factory=StandardInput)
    preprocess: PreprocessResult = Field(default_factory=PreprocessResult)


class StandardResponse(BaseModel):
    """Full standardized review response / result."""
    request_id: str = ""
    created_at: str = ""
    input: StandardInput = Field(default_factory=StandardInput)
    preprocess: PreprocessResult = Field(default_factory=PreprocessResult)
    review: ThreeLayerReview = Field(default_factory=ThreeLayerReview)
    case_references: list[CaseReference] = Field(default_factory=list)
    rewrite_templates: list[RewriteTemplate] = Field(default_factory=list)
    penalty_assessment: PenaltyAssessment = Field(default_factory=PenaltyAssessment)
    final_result: FinalResult = Field(default_factory=FinalResult)
