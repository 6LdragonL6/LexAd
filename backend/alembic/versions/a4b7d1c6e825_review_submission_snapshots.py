"""add immutable review submission snapshots

Revision ID: a4b7d1c6e825
Revises: f3a8c2d9e714
Create Date: 2026-07-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a4b7d1c6e825"
down_revision: Union[str, None] = "f3a8c2d9e714"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "material_submission_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("material_id", sa.String(length=36), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("industry", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("platforms", sa.JSON(), nullable=False),
        sa.Column("material_type", sa.String(length=30), nullable=False, server_default="文字"),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("material_id", "version", name="uq_material_snapshot_version"),
    )
    op.create_index("ix_material_submission_snapshots_material_id", "material_submission_snapshots", ["material_id"])
    op.add_column("reviews", sa.Column("submission_snapshot_id", sa.String(length=36), nullable=True))
    op.create_index("ix_reviews_submission_snapshot_id", "reviews", ["submission_snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_submission_snapshot_id", table_name="reviews")
    op.drop_column("reviews", "submission_snapshot_id")
    op.drop_index("ix_material_submission_snapshots_material_id", table_name="material_submission_snapshots")
    op.drop_table("material_submission_snapshots")
