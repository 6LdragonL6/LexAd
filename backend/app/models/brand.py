import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, Integer, JSON, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BrandStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class BrandIndustrySuggestionStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    ignored = "ignored"


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    industry: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[BrandStatus] = mapped_column(
        SAEnum(BrandStatus), nullable=False, default=BrandStatus.active, index=True
    )
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    industry_links: Mapped[list["BrandIndustry"]] = relationship(
        "BrandIndustry",
        lazy="selectin",
        cascade="all, delete-orphan",
        foreign_keys="BrandIndustry.brand_id",
    )

    @property
    def industries(self) -> list[str]:
        return sorted(link.industry for link in self.industry_links)


class BrandIndustry(Base):
    __tablename__ = "brand_industries"
    __table_args__ = (UniqueConstraint("brand_id", "industry", name="uq_brand_industry"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id: Mapped[str] = mapped_column(String(36), ForeignKey("brands.id"), nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BrandIndustrySuggestion(Base):
    __tablename__ = "brand_industry_suggestions"
    __table_args__ = (UniqueConstraint("brand_id", "industry", name="uq_brand_industry_suggestion"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id: Mapped[str] = mapped_column(String(36), ForeignKey("brands.id"), nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[BrandIndustrySuggestionStatus] = mapped_column(
        SAEnum(BrandIndustrySuggestionStatus),
        nullable=False,
        default=BrandIndustrySuggestionStatus.pending,
        index=True,
    )
    first_material_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("materials.id"), nullable=True)
    latest_material_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("materials.id"), nullable=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
