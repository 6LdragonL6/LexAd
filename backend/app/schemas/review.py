from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from app.schemas.material import SubmissionSnapshotOut


class BasisReference(BaseModel):
    id: str
    title: str
    version: str = ""


class VerificationItem(BaseModel):
    item_id: str
    evidence_quote: str
    verification_type: str
    reason: str
    required_materials: list[str] = Field(default_factory=list)
    basis_refs: list[BasisReference] = Field(default_factory=list)


class MatchedRule(BaseModel):
    rule_id: str
    rule_text: str
    source_law: str = ""
    match_type: str = "keyword"
    explanation: str = ""
    matched_text: str = ""
    match_method: str = "keyword"
    score: float | None = None
    source_id: str = ""
    suggestion: str = ""
    evidence_quote: str = ""
    reasoning: str = ""
    risk_level: str = "medium"
    risk_level_label: str = "中风险"
    confidence: int = 0
    adjudication_status: str = "confirmed"
    basis_refs: list[BasisReference] = Field(default_factory=list)


class LayerResult(BaseModel):
    layer: str
    matched_rules: list[MatchedRule] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    status: str = "no_match"
    source_versions: list[str] = Field(default_factory=list)
    candidate_count: int = 0
    verification_items: list[VerificationItem] = Field(default_factory=list)
    requires_manual_review: bool = False


class EngineResult(BaseModel):
    compliance_score: int = Field(default=100, ge=0, le=100)
    layer1: LayerResult = Field(default_factory=lambda: LayerResult(layer="硬规则匹配"))
    layer2: LayerResult = Field(default_factory=lambda: LayerResult(layer="语义推理"))
    layer3: LayerResult = Field(default_factory=lambda: LayerResult(layer="证明材料检查"))
    layer4: LayerResult = Field(default_factory=lambda: LayerResult(layer="平台差异适配"))
    summary: str = ""
    suggestions: list[str] = Field(default_factory=list)
    case_refs: list[dict] = Field(default_factory=list)
    platform_rule_version_ids: list[str] = Field(default_factory=list)
    unavailable_platforms: list[str] = Field(default_factory=list)
    platform_version_labels: dict[str, str] = Field(default_factory=dict)
    hit_count: int = 0
    risk_topics: list[str] = Field(default_factory=list)
    verification_items: list[VerificationItem] = Field(default_factory=list)
    requires_manual_review: bool = False
    review_status: str = "completed"


class AIReviewRequest(BaseModel):
    material_id: str


class ReviewStageOut(BaseModel):
    key: str
    label: str
    status: str = Field(pattern="^(pending|running|completed|manual_review|failed)$")

class ReviewOut(BaseModel):
    id: str
    material_id: str
    version: int
    legal_compliance_score: int = Field(ge=0, le=100)
    public_opinion_safety_score: int | None = Field(default=None, ge=0, le=100)
    ai_result: dict
    task_status: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    legal_library_version_id: str | None = None
    industry_library_version_id: str | None = None
    platform_rule_version_ids: list = Field(default_factory=list)
    public_opinion_library_version_id: str | None = None
    legal_module_status: str | None = None
    legal_module_error: str | None = None
    legal_module_retry_count: int = 0
    legal_module_completed_at: datetime | None = None
    public_opinion_module_status: str | None = None
    public_opinion_result: dict = Field(default_factory=dict)
    public_opinion_module_error: str | None = None
    public_opinion_module_retry_count: int = 0
    public_opinion_module_completed_at: datetime | None = None
    legal_decision: str | None
    legal_notes: str | None
    return_reasons: str | None
    reviewer_id: str | None
    reviewed_at: datetime | None
    created_at: datetime
    submission: SubmissionSnapshotOut | None = None
    stages: list[ReviewStageOut] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_stages(self):
        from app.schemas.review_progress import build_review_stages

        self.stages = [ReviewStageOut(**stage) for stage in build_review_stages(
            task_status=self.task_status,
            legal_module_status=self.legal_module_status,
            public_opinion_module_status=self.public_opinion_module_status,
            ai_result=self.ai_result,
            public_opinion_result=self.public_opinion_result,
        )]
        return self

    model_config = {"from_attributes": True}

class LegalDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|returned|conditional)$")
    notes: str = ""
    return_reasons: str = ""
    public_opinion_manually_reviewed: bool = False

    @model_validator(mode="after")
    def conditional_requires_notes(self):
        if self.decision == "conditional" and not self.notes.strip():
            raise ValueError("有条件通过必须填写附加条件")
        return self

class ReviewQueueItem(BaseModel):
    id: str
    material_id: str
    material_name: str
    submitter_name: str
    industry: str
    legal_compliance_score: int = Field(ge=0, le=100)
    public_opinion_safety_score: int | None = Field(default=None, ge=0, le=100)
    priority: str
    status: str
    created_at: datetime
    waiting_hours: float = 0
    legal_decision: str | None = None
    return_reasons: str | None = None
    legal_notes: str | None = None
    version: int = 1
    material_version: int = 1
