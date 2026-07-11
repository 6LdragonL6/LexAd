from datetime import datetime
from pydantic import BaseModel, Field


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    industry: str = Field(default="", max_length=50)


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    aliases: list[str] | None = None
    industry: str | None = Field(default=None, max_length=50)
    description: str | None = None
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class BrandOut(BaseModel):
    id: str
    name: str
    aliases: list[str]
    industry: str
    description: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BrandCreateResponse(BaseModel):
    brand: BrandOut
    created: bool


class TopViolation(BaseModel):
    rule_id: str
    rule_text: str
    count: int


class RecentReview(BaseModel):
    id: str
    version: int
    ai_risk_score: int
    legal_decision: str | None
    created_at: str


class ApprovedMaterial(BaseModel):
    id: str
    name: str
    raw_text_preview: str


class BrandProfile(BaseModel):
    brand: BrandOut
    total_materials: int
    total_reviews: int
    decided_reviews: int
    approved_count: int
    pass_rate: float | None
    avg_versions: float | None
    top_violations: list[TopViolation]
    recent_reviews: list[RecentReview]
    approved_materials: list[ApprovedMaterial]
