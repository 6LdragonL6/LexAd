"""v0.7.1 version consistency and brand industries

Revision ID: b8d4e1f7a203
Revises: 7c2d9a4e6f81
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import re
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8d4e1f7a203"
down_revision: Union[str, None] = "7c2d9a4e6f81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_split_re = re.compile(r"[、,，;；/|]+")


def _split(value: str | None) -> list[str]:
    result: list[str] = []
    for item in _split_re.split(value or ""):
        normalized = item.strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def upgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(200), nullable=True))

    bind = op.get_bind()
    bind.execute(sa.text("UPDATE materials SET display_name = name WHERE display_name IS NULL OR display_name = ''"))

    with op.batch_alter_table("materials") as batch_op:
        batch_op.alter_column("display_name", existing_type=sa.String(200), nullable=False)

    suggestion_status = sa.Enum("pending", "accepted", "ignored", name="brandindustrysuggestionstatus")

    op.create_table(
        "brand_industries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("brand_id", sa.String(36), nullable=False),
        sa.Column("industry", sa.String(50), nullable=False),
        sa.Column("created_by_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "industry", name="uq_brand_industry"),
    )
    op.create_index(op.f("ix_brand_industries_brand_id"), "brand_industries", ["brand_id"])
    op.create_index(op.f("ix_brand_industries_industry"), "brand_industries", ["industry"])

    op.create_table(
        "brand_industry_suggestions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("brand_id", sa.String(36), nullable=False),
        sa.Column("industry", sa.String(50), nullable=False),
        sa.Column("status", suggestion_status, nullable=False),
        sa.Column("first_material_id", sa.String(36), nullable=True),
        sa.Column("latest_material_id", sa.String(36), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by_id", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["first_material_id"], ["materials.id"]),
        sa.ForeignKeyConstraint(["latest_material_id"], ["materials.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "industry", name="uq_brand_industry_suggestion"),
    )
    op.create_index(op.f("ix_brand_industry_suggestions_brand_id"), "brand_industry_suggestions", ["brand_id"])
    op.create_index(op.f("ix_brand_industry_suggestions_industry"), "brand_industry_suggestions", ["industry"])
    op.create_index(op.f("ix_brand_industry_suggestions_status"), "brand_industry_suggestions", ["status"])

    _backfill_brand_industries(bind)


def _backfill_brand_industries(bind) -> None:
    now = datetime.now(timezone.utc)
    brands = bind.execute(sa.text("SELECT id, industry, created_by_id FROM brands WHERE deleted_at IS NULL")).mappings().all()
    accepted: dict[str, set[str]] = defaultdict(set)

    for brand in brands:
        for industry in _split(brand["industry"]):
            accepted[brand["id"]].add(industry)
            bind.execute(
                sa.text(
                    "INSERT INTO brand_industries (id, brand_id, industry, created_by_id, created_at) "
                    "VALUES (:id, :brand_id, :industry, :created_by_id, :created_at)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "brand_id": brand["id"],
                    "industry": industry,
                    "created_by_id": brand["created_by_id"],
                    "created_at": now,
                },
            )

    rows = bind.execute(
        sa.text(
            "SELECT id, brand_id, industry, created_at FROM materials "
            "WHERE brand_id IS NOT NULL AND deleted_at IS NULL ORDER BY created_at ASC"
        )
    ).mappings().all()
    aggregate: dict[tuple[str, str], dict] = {}
    for row in rows:
        for industry in _split(row["industry"]):
            if industry in accepted[row["brand_id"]]:
                continue
            key = (row["brand_id"], industry)
            item = aggregate.setdefault(
                key,
                {
                    "first_material_id": row["id"],
                    "latest_material_id": row["id"],
                    "occurrence_count": 0,
                    "first_seen_at": row["created_at"] or now,
                    "last_seen_at": row["created_at"] or now,
                },
            )
            item["occurrence_count"] += 1
            item["latest_material_id"] = row["id"]
            item["last_seen_at"] = row["created_at"] or now

    for (brand_id, industry), item in aggregate.items():
        bind.execute(
            sa.text(
                "INSERT INTO brand_industry_suggestions "
                "(id, brand_id, industry, status, first_material_id, latest_material_id, occurrence_count, "
                "first_seen_at, last_seen_at, reviewed_by_id, reviewed_at) "
                "VALUES (:id, :brand_id, :industry, 'pending', :first_material_id, :latest_material_id, "
                ":occurrence_count, :first_seen_at, :last_seen_at, NULL, NULL)"
            ),
            {"id": str(uuid.uuid4()), "brand_id": brand_id, "industry": industry, **item},
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_brand_industry_suggestions_status"), table_name="brand_industry_suggestions")
    op.drop_index(op.f("ix_brand_industry_suggestions_industry"), table_name="brand_industry_suggestions")
    op.drop_index(op.f("ix_brand_industry_suggestions_brand_id"), table_name="brand_industry_suggestions")
    op.drop_table("brand_industry_suggestions")
    op.drop_index(op.f("ix_brand_industries_industry"), table_name="brand_industries")
    op.drop_index(op.f("ix_brand_industries_brand_id"), table_name="brand_industries")
    op.drop_table("brand_industries")

    with op.batch_alter_table("materials") as batch_op:
        batch_op.drop_column("display_name")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="brandindustrysuggestionstatus").drop(bind, checkfirst=True)
