"""v0.4.1 review task status

Revision ID: 9e4f1a2c7b30
Revises: bedaa881e856
Create Date: 2026-07-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9e4f1a2c7b30"
down_revision: Union[str, None] = "bedaa881e856"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column("task_status", sa.String(length=20), nullable=False, server_default="completed"),
    )
    op.add_column("reviews", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("reviews", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reviews", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_reviews_task_status", "reviews", ["task_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reviews_task_status", table_name="reviews")
    op.drop_column("reviews", "completed_at")
    op.drop_column("reviews", "started_at")
    op.drop_column("reviews", "error_message")
    op.drop_column("reviews", "task_status")
