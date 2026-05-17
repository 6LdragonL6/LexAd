from datetime import datetime
from pydantic import BaseModel, Field

class MaterialSubmit(BaseModel):
    name: str = Field(..., max_length=200)
    industry: str = Field(default="", max_length=50)
    platforms: list[str] = Field(default_factory=list)
    material_type: str = Field(default="文字")
    raw_text: str = Field(default="")
    priority: str = Field(default="normal", pattern="^(normal|urgent|extreme)$")
    deadline: datetime | None = None

class MaterialUpdate(BaseModel):
    name: str | None = None
    raw_text: str | None = None
    platforms: list[str] | None = None
    priority: str | None = None
    deadline: datetime | None = None

class MaterialOut(BaseModel):
    id: str
    name: str
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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class MaterialListItem(BaseModel):
    id: str
    name: str
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
