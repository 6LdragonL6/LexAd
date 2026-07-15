from datetime import datetime
from pydantic import BaseModel, Field


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    industry: str = Field(default="", max_length=50)
    industries: list[str] = Field(default_factory=list)


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    aliases: list[str] | None = None
    industry: str | None = Field(default=None, max_length=50)
    industries: list[str] | None = None
    description: str | None = None
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class BrandOut(BaseModel):
    id: str
    name: str
    aliases: list[str]
    industry: str
    industries: list[str] = Field(default_factory=list)
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
    legal_compliance_score: int
    public_opinion_safety_score: int | None = None
    legal_decision: str | None
    created_at: str


class ApprovedMaterial(BaseModel):
    id: str
    name: str
    raw_text_preview: str


class BrandIndustrySuggestionOut(BaseModel):
    id: str
    industry: str
    status: str
    first_material_id: str | None
    latest_material_id: str | None
    latest_material_name: str = ""
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class BrandIndustryUpdate(BaseModel):
    industries: list[str]


class BrandIndustrySuggestionAction(BaseModel):
    action: str = Field(..., pattern="^(accept|ignore|restore)$")


class BrandMemoryItem(BaseModel):
    text: str
    count: int


class BrandRecentDecisions(BaseModel):
    approved: int = 0
    conditional: int = 0
    returned: int = 0


class BrandMemoryImpression(BaseModel):
    status: str = Field(default="collecting", pattern="^(collecting|stable|mixed|attention)$")
    headline: str = "样本积累中"
    summary: str = "尚无足够历史审核形成稳定品牌印象。"
    completed_review_count: int = 0
    decided_review_count: int = 0
    recent_decisions: BrandRecentDecisions = Field(default_factory=BrandRecentDecisions)
    avg_versions: float | None = None
    revision_tendency: str = "暂无修改轮次参考"
    frequent_risks: list[BrandMemoryItem] = Field(default_factory=list)
    common_suggestions: list[BrandMemoryItem] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)


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
    industry_suggestions: list[BrandIndustrySuggestionOut] = Field(default_factory=list)
    memory_impression: BrandMemoryImpression = Field(default_factory=BrandMemoryImpression)
