"""v0.5.0 add archived to materialstatus

Revision ID: d8a1f0e3b5c6
Revises: c7f4a8b9d012
Create Date: 2026-07-08
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "d8a1f0e3b5c6"
down_revision: Union[str, None] = "c7f4a8b9d012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        # Check if the value already exists before adding
        existing = bind.execute(
            text(
                "SELECT 1 FROM pg_enum "
                "WHERE enumtypid = 'materialstatus'::regtype "
                "AND enumlabel = 'archived'"
            )
        ).fetchone()
        if not existing:
            # PostgreSQL requires ALTER TYPE ADD VALUE to run outside a transaction block.
            with op.get_context().autocommit_block():
                op.execute("ALTER TYPE materialstatus ADD VALUE 'archived'")
    elif dialect_name == "sqlite":
        # SQLite stores enums as VARCHAR, model change is sufficient
        pass
    else:
        # MySQL / other: attempt ALTER, let it fail visibly if unsupported
        op.execute("ALTER TYPE materialstatus ADD VALUE 'archived'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # No safe automatic downgrade path for this change.
    pass
