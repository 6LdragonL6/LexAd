import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PublicOpinionEventStatus(str, enum.Enum):
    draft = "draft"
    ai_processing = "ai_processing"
    pending_review = "pending_review"
    published = "published"
    archived = "archived"


class PlatformRuleStatus(str, enum.Enum):
    draft = "draft"
    pending_effective = "pending_effective"
    active = "active"
    expired = "expired"


class KnowledgeImportJobStatus(str, enum.Enum):
    uploaded = "uploaded"
    validated = "validated"
    validation_failed = "validation_failed"
    importing = "importing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ReviewModuleStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    unavailable = "unavailable"


PUBLIC_OPINION_EVENT_TRANSITIONS: dict[
    PublicOpinionEventStatus,
    set[PublicOpinionEventStatus],
] = {
    PublicOpinionEventStatus.draft: {
        PublicOpinionEventStatus.ai_processing,
        PublicOpinionEventStatus.pending_review,
    },
    PublicOpinionEventStatus.ai_processing: {
        PublicOpinionEventStatus.pending_review,
        PublicOpinionEventStatus.draft,
    },
    PublicOpinionEventStatus.pending_review: {
        PublicOpinionEventStatus.ai_processing,
        PublicOpinionEventStatus.draft,
        PublicOpinionEventStatus.published,
    },
    PublicOpinionEventStatus.published: {
        PublicOpinionEventStatus.archived,
    },
    PublicOpinionEventStatus.archived: {
        PublicOpinionEventStatus.published,
    },
}


class PublicOpinionEvent(Base):
    __tablename__ = "public_opinion_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    source_text: Mapped[str] = mapped_column(Text, default="")
    consequence_text: Mapped[str] = mapped_column(Text, default="")
    source_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[PublicOpinionEventStatus] = mapped_column(
        SAEnum(PublicOpinionEventStatus),
        default=PublicOpinionEventStatus.draft,
        index=True,
    )
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    updated_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    published_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    archived_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    restored_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def can_transition_to(self, next_status: PublicOpinionEventStatus) -> bool:
        current = _normalize_public_opinion_status(self.status)
        target = _normalize_public_opinion_status(next_status)
        return target in PUBLIC_OPINION_EVENT_TRANSITIONS[current]

    def transition_to(self, next_status: PublicOpinionEventStatus) -> None:
        target = _normalize_public_opinion_status(next_status)
        if not self.can_transition_to(target):
            raise ValueError(f"Invalid public opinion event transition: {self.status} -> {target}")
        self.status = target

    def can_delete(self) -> bool:
        return _normalize_public_opinion_status(self.status) == PublicOpinionEventStatus.draft


class PublicOpinionEventVersion(Base):
    __tablename__ = "public_opinion_event_versions"
    __table_args__ = (
        UniqueConstraint("event_id", "version", name="uq_public_opinion_event_versions_event_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("public_opinion_events.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200), default="")
    industry: Mapped[list] = mapped_column(JSON, default=list)
    platforms: Mapped[list] = mapped_column(JSON, default=list)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_text: Mapped[str] = mapped_column(Text, default="")
    sources: Mapped[list] = mapped_column(JSON, default=list)
    event_process: Mapped[dict] = mapped_column(JSON, default=dict)
    consequences: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_topics: Mapped[list] = mapped_column(JSON, default=list)
    trigger_patterns: Mapped[list] = mapped_column(JSON, default=list)
    affected_groups: Mapped[list] = mapped_column(JSON, default=list)
    propagation_drivers: Mapped[list] = mapped_column(JSON, default=list)
    normalized_tags: Mapped[dict] = mapped_column(JSON, default=dict)
    severity_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edited_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    edit_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PublicOpinionLibraryVersion(Base):
    __tablename__ = "public_opinion_library_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    event_ids: Mapped[list] = mapped_column(JSON, default=list)
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PlatformRuleSet(Base):
    __tablename__ = "platform_rule_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PlatformRuleVersion(Base):
    __tablename__ = "platform_rule_versions"
    __table_args__ = (
        UniqueConstraint("rule_set_id", "version_label", name="uq_platform_rule_versions_set_label"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_set_id: Mapped[str] = mapped_column(String(36), ForeignKey("platform_rule_sets.id"), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(100), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    structured_rules: Mapped[list] = mapped_column(JSON, default=list)
    diff_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[PlatformRuleStatus] = mapped_column(
        SAEnum(PlatformRuleStatus),
        default=PlatformRuleStatus.draft,
        index=True,
    )
    imported_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    reviewed_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    activated_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def is_effective_at(self, moment: datetime) -> bool:
        if _normalize_platform_rule_status(self.status) != PlatformRuleStatus.active:
            return False
        if self.effective_at and moment < _as_utc(self.effective_at):
            return False
        return not (self.expires_at and moment >= _as_utc(self.expires_at))


class KnowledgeImportJob(Base):
    __tablename__ = "knowledge_import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    import_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[KnowledgeImportJobStatus] = mapped_column(
        SAEnum(KnowledgeImportJobStatus),
        default=KnowledgeImportJobStatus.uploaded,
        index=True,
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    valid_items: Mapped[int] = mapped_column(Integer, default=0)
    invalid_items: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeAuditLog(Base):
    __tablename__ = "knowledge_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    before_state: Mapped[dict] = mapped_column(JSON, default=dict)
    after_state: Mapped[dict] = mapped_column(JSON, default=dict)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def _normalize_public_opinion_status(
    status: PublicOpinionEventStatus | str | None,
) -> PublicOpinionEventStatus:
    if status is None:
        return PublicOpinionEventStatus.draft
    return status if isinstance(status, PublicOpinionEventStatus) else PublicOpinionEventStatus(status)


def _normalize_platform_rule_status(status: PlatformRuleStatus | str) -> PlatformRuleStatus:
    return status if isinstance(status, PlatformRuleStatus) else PlatformRuleStatus(status)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
