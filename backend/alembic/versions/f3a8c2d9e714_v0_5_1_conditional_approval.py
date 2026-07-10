"""v0.5.1 add conditional approval material status

Revision ID: f3a8c2d9e714
Revises: d8a1f0e3b5c6
Create Date: 2026-07-11
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "f3a8c2d9e714"
down_revision: Union[str, None] = "d8a1f0e3b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        existing = bind.execute(
            text(
                "SELECT 1 FROM pg_enum "
                "WHERE enumtypid = 'materialstatus'::regtype "
                "AND enumlabel = 'conditional_approved'"
            )
        ).fetchone()
        if not existing:
            with op.get_context().autocommit_block():
                op.execute("ALTER TYPE materialstatus ADD VALUE 'conditional_approved'")
    elif bind.dialect.name != "sqlite":
        op.execute("ALTER TYPE materialstatus ADD VALUE 'conditional_approved'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely.
    pass
