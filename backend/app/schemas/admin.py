from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ApiKeyUpdate(BaseModel):
    api_key: str = Field(min_length=8, max_length=512)

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        normalized = value.strip()
        if any(ord(char) < 32 for char in normalized):
            raise ValueError("API Key 不能包含控制字符")
        return normalized


class AiConfigStatus(BaseModel):
    configured: bool
    provider: str = "DeepSeek"
    base_url: str
    model: str
    masked_key: str = ""
    source: Literal["database", "environment", "none"] = "none"
    validation_status: str = "unconfigured"
    last_error: str = ""
    updated_at: datetime | None = None
    validated_at: datetime | None = None
    updated_by_id: str | None = None


class AiConfigTestResult(BaseModel):
    ok: bool
    message: str
    tested_at: datetime


class RecycleBinEntryOut(BaseModel):
    id: str
    target_type: str
    target_id: str
    display_name: str
    deleted_by_id: str
    deleted_at: datetime
    purge_after: datetime
    remaining_days: int


class RecycleBinList(BaseModel):
    items: list[RecycleBinEntryOut]
    total: int
    page: int
    page_size: int


class DeleteTargetRequest(BaseModel):
    target_type: Literal["material", "brand", "public_opinion_event", "platform_rule_set"]
    target_id: str = Field(min_length=1, max_length=36)
