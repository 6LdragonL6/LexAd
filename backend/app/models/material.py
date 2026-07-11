import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, Enum as SAEnum, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
import enum


class MaterialStatus(str, enum.Enum):
    draft = "draft"
    ai_reviewing = "ai_reviewing"
    pending_legal = "pending_legal"
    in_legal_review = "in_legal_review"
    approved = "approved"
    conditional_approved = "conditional_approved"
    returned = "returned"
    archived = "archived"


class MaterialPriority(str, enum.Enum):
    normal = "normal"
    urgent = "urgent"
    extreme = "extreme"


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(50), default="")
    platforms: Mapped[dict] = mapped_column(JSON, default=list)
    material_type: Mapped[str] = mapped_column(String(30), default="文字")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priority: Mapped[MaterialPriority] = mapped_column(SAEnum(MaterialPriority), default=MaterialPriority.normal)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[MaterialStatus] = mapped_column(SAEnum(MaterialStatus), default=MaterialStatus.draft)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    submitter_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    brand_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("brands.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class MaterialSubmissionSnapshot(Base):
    __tablename__ = "material_submission_snapshots"
    __table_args__ = (UniqueConstraint("material_id", "version", name="uq_material_snapshot_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    material_id: Mapped[str] = mapped_column(String(36), ForeignKey("materials.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(50), default="")
    platforms: Mapped[list] = mapped_column(JSON, default=list)
    material_type: Mapped[str] = mapped_column(String(30), default="文字")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
