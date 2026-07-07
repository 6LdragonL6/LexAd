from datetime import datetime
from pydantic import BaseModel, Field

class MatchedRule(BaseModel):
    rule_id: str
    rule_text: str
    source_law: str = ""
    match_type: str = "keyword"
    explanation: str = ""

class LayerResult(BaseModel):
    layer: str
    matched_rules: list[MatchedRule] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)

class EngineResult(BaseModel):
    risk_score: int = 100
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

class AIReviewRequest(BaseModel):
    material_id: str

class ReviewOut(BaseModel):
    id: str
    material_id: str
    version: int
    ai_risk_score: int
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

    model_config = {"from_attributes": True}

class LegalDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|returned|conditional)$")
    notes: str = ""
    return_reasons: str = ""

class ReviewQueueItem(BaseModel):
    id: str
    material_id: str
    material_name: str
    submitter_name: str
    industry: str
    ai_risk_score: int
    priority: str
    status: str
    created_at: datetime
    waiting_hours: float = 0
    legal_decision: str | None = None
    return_reasons: str | None = None
    legal_notes: str | None = None
    version: int = 1
    material_version: int = 1
