from datetime import datetime
from pydantic import BaseModel, Field

class MatchedRule(BaseModel):
    rule_id: str
    rule_text: str
    source_law: str = ""
    match_type: str = "keyword"

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
