import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.knowledge import ReviewModuleStatus
import enum


class LegalDecision(str, enum.Enum):
    approved = "approved"
    returned = "returned"
    conditional = "conditional"


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    material_id: Mapped[str] = mapped_column(String(36), ForeignKey("materials.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    ai_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    ai_result: Mapped[dict] = mapped_column(JSON, default=dict)
    task_status: Mapped[str] = mapped_column(String(20), default="processing", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    legal_library_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    industry_library_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    platform_rule_version_ids: Mapped[list] = mapped_column(JSON, default=list)
    public_opinion_library_version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("public_opinion_library_versions.id"),
        nullable=True,
    )
    legal_module_status: Mapped[ReviewModuleStatus] = mapped_column(
        SAEnum(ReviewModuleStatus),
        default=ReviewModuleStatus.pending,
        index=True,
    )
    legal_module_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_module_retry_count: Mapped[int] = mapped_column(Integer, default=0)
    legal_module_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    public_opinion_module_status: Mapped[ReviewModuleStatus] = mapped_column(
        SAEnum(ReviewModuleStatus),
        default=ReviewModuleStatus.pending,
        index=True,
    )
    public_opinion_result: Mapped[dict] = mapped_column(JSON, default=dict)
    public_opinion_module_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_opinion_module_retry_count: Mapped[int] = mapped_column(Integer, default=0)
    public_opinion_module_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    legal_decision: Mapped[LegalDecision | None] = mapped_column(SAEnum(LegalDecision), nullable=True)
    legal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    return_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
