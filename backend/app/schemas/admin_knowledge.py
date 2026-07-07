from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PublicOpinionEventCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=100)
    title: str = Field(default="", max_length=200)
    source_text: str = Field(default="")
    consequence_text: str = Field(default="")
    source_meta: dict[str, Any] = Field(default_factory=dict)


class PublicOpinionEventUpdate(BaseModel):
    external_id: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=200)
    source_text: str | None = None
    consequence_text: str | None = None
    source_meta: dict[str, Any] | None = None


class PublicOpinionEventOut(BaseModel):
    id: str
    external_id: str | None
    title: str
    source_text: str
    consequence_text: str
    source_meta: dict
    status: str
    created_by_id: str
    updated_by_id: str | None
    published_by_id: str | None
    archived_by_id: str | None
    restored_by_id: str | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    archived_at: datetime | None

    model_config = {"from_attributes": True}


class PublicOpinionEventVersionOut(BaseModel):
    id: str
    event_id: str
    version: int
    title: str
    industry: list
    platforms: list
    occurred_at: datetime | None
    source_text: str
    sources: list
    event_process: dict
    consequences: dict
    risk_topics: list
    trigger_patterns: list
    affected_groups: list
    propagation_drivers: list
    normalized_tags: dict
    severity_level: str | None
    summary: str
    confidence: int | None
    model_name: str | None
    model_version: str | None
    generated_at: datetime | None
    edited_by_id: str | None
    edit_notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PublicOpinionEventDetail(BaseModel):
    event: PublicOpinionEventOut
    versions: list[PublicOpinionEventVersionOut] = Field(default_factory=list)


class PublicOpinionEventList(BaseModel):
    items: list[PublicOpinionEventOut]
    total: int


class PlatformRuleSetCreate(BaseModel):
    platform_name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: str = ""


class PlatformRuleSetUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    description: str | None = None


class PlatformRuleSetOut(BaseModel):
    id: str
    platform_name: str
    display_name: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlatformRuleVersionCreate(BaseModel):
    version_label: str = Field(..., min_length=1, max_length=100)
    source_name: str = ""
    source_url: str = ""
    published_at: datetime | None = None
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    raw_text: str = ""
    structured_rules: list[dict[str, Any]] = Field(default_factory=list)


class PlatformRuleVersionOut(BaseModel):
    id: str
    rule_set_id: str
    version_label: str
    source_name: str
    source_url: str
    published_at: datetime | None
    effective_at: datetime | None
    expires_at: datetime | None
    raw_text: str
    structured_rules: list
    diff_summary: dict
    status: str
    imported_by_id: str
    reviewed_by_id: str | None
    activated_by_id: str | None
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None

    model_config = {"from_attributes": True}


class PlatformRuleSetDetail(BaseModel):
    rule_set: PlatformRuleSetOut
    active_version: PlatformRuleVersionOut | None = None
    versions: list[PlatformRuleVersionOut] = Field(default_factory=list)


class PlatformRuleSetList(BaseModel):
    items: list[PlatformRuleSetDetail]
    total: int


class KnowledgeImportJobOut(BaseModel):
    id: str
    import_type: str
    file_name: str
    status: str
    total_items: int
    valid_items: int
    invalid_items: int
    error_summary: dict
    options: dict
    created_by_id: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PublicOpinionImportPreviewRequest(BaseModel):
    payload: dict[str, Any]
    file_name: str = "inline-json"


class PublicOpinionImportConfirmRequest(BaseModel):
    duplicate_actions: dict[str, str] = Field(default_factory=dict)
    run_structure: bool = False


class KnowledgeImportConfirmResult(BaseModel):
    job: KnowledgeImportJobOut
    created_event_ids: list[str] = Field(default_factory=list)
    updated_event_ids: list[str] = Field(default_factory=list)
    skipped_external_ids: list[str] = Field(default_factory=list)


class KnowledgeAuditLogOut(BaseModel):
    id: str
    actor_id: str
    action: str
    target_type: str
    target_id: str
    before_state: dict
    after_state: dict
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
