from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.engine.industry import format_industries, validate_industries


def _validated_industry(value: str | None) -> str | None:
    if value is None:
        return None
    return format_industries(validate_industries(value))

class MaterialSubmit(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    industry: str = Field(default="", max_length=50)
    platforms: list[str] = Field(default_factory=list, max_length=10)
    material_type: str = Field(default="文字", min_length=1, max_length=30)
    raw_text: str = Field(default="", max_length=50_000)
    priority: str = Field(default="normal", pattern="^(normal|urgent|extreme)$")
    deadline: datetime | None = None
    brand_id: str | None = None

    _validate_industry = field_validator("industry")(_validated_industry)

class MaterialUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    raw_text: str | None = Field(default=None, max_length=50_000)
    industry: str | None = Field(default=None, max_length=50)
    platforms: list[str] | None = Field(default=None, max_length=10)
    priority: str | None = Field(default=None, pattern="^(normal|urgent|extreme)$")
    deadline: datetime | None = None
    brand_id: str | None = None

    _validate_industry = field_validator("industry")(_validated_industry)


class MaterialResubmit(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    raw_text: str = Field(..., min_length=1, max_length=50_000)
    industry: str = Field(..., min_length=1, max_length=50)
    platforms: list[str] = Field(..., min_length=1, max_length=10)
    material_type: str = Field(default="文字", min_length=1, max_length=30)
    priority: str = Field(default="normal", pattern="^(normal|urgent|extreme)$")
    deadline: datetime | None = None

    _validate_industry = field_validator("industry")(_validated_industry)
    model_config = {"extra": "forbid"}

class MaterialOut(BaseModel):
    id: str
    name: str
    display_name: str
    industry: str
    platforms: list
    material_type: str
    raw_text: str
    image_path: str | None
    priority: str
    deadline: datetime | None
    status: str
    current_version: int
    submitter_id: str
    brand_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class MaterialListItem(BaseModel):
    id: str
    name: str
    display_name: str
    industry: str
    priority: str
    status: str
    current_version: int
    submitter_id: str
    created_at: datetime

    model_config = {"from_attributes": True}

class PreviewTextResponse(BaseModel):
    text: str
    quality: str
    source_format: str


class SubmissionSnapshotOut(BaseModel):
    name: str
    raw_text: str
    industry: str
    platforms: list[str]
    material_type: str
    priority: str
    deadline: datetime | None

    model_config = {"from_attributes": True}
