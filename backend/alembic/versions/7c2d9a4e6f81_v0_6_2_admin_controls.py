"""v0.6.2 admin controls and recycle bin

Revision ID: 7c2d9a4e6f81
Revises: 294f05fbf95c
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c2d9a4e6f81"
down_revision: Union[str, None] = "294f05fbf95c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SOFT_DELETE_TABLES = (
    "materials",
    "brands",
    "public_opinion_events",
    "platform_rule_sets",
)


def upgrade() -> None:
    op.create_table(
        "secure_settings",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(16), nullable=False, server_default=""),
        sa.Column("validation_status", sa.String(30), nullable=False, server_default="unverified"),
        sa.Column("last_error", sa.String(100), nullable=False, server_default=""),
        sa.Column("updated_by_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_secure_settings_key", "secure_settings", ["key"], unique=True)

    op.create_table(
        "recycle_bin_entries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("deleted_by_id", sa.String(36), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_state", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_type", "target_id", name="uq_recycle_bin_target"),
    )
    for column in ("target_type", "target_id", "deleted_by_id", "deleted_at", "purge_after"):
        op.create_index(f"ix_recycle_bin_entries_{column}", "recycle_bin_entries", [column])

    for table_name in SOFT_DELETE_TABLES:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
            batch_op.add_column(sa.Column("deleted_by_id", sa.String(36), nullable=True))
            batch_op.add_column(sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table_name}_deleted_by_id", "users", ["deleted_by_id"], ["id"]
            )
            batch_op.create_index(f"ix_{table_name}_deleted_at", ["deleted_at"])
            batch_op.create_index(f"ix_{table_name}_purge_after", ["purge_after"])


def downgrade() -> None:
    for table_name in reversed(SOFT_DELETE_TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_purge_after")
            batch_op.drop_index(f"ix_{table_name}_deleted_at")
            batch_op.drop_constraint(f"fk_{table_name}_deleted_by_id", type_="foreignkey")
            batch_op.drop_column("purge_after")
            batch_op.drop_column("deleted_by_id")
            batch_op.drop_column("deleted_at")

    op.drop_table("recycle_bin_entries")
    op.drop_table("secure_settings")
