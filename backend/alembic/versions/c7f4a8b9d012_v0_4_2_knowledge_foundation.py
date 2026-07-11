"""v0.4.2 knowledge foundation

Revision ID: c7f4a8b9d012
Revises: 9e4f1a2c7b30
Create Date: 2026-07-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7f4a8b9d012"
down_revision: Union[str, None] = "9e4f1a2c7b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


public_opinion_event_status = sa.Enum(
    "draft",
    "ai_processing",
    "pending_review",
    "published",
    "archived",
    name="publicopinioneventstatus",
)
platform_rule_status = sa.Enum(
    "draft",
    "pending_effective",
    "active",
    "expired",
    name="platformrulestatus",
)
knowledge_import_job_status = sa.Enum(
    "uploaded",
    "validated",
    "validation_failed",
    "importing",
    "completed",
    "failed",
    "cancelled",
    name="knowledgeimportjobstatus",
)
review_module_status = sa.Enum(
    "pending",
    "running",
    "succeeded",
    "failed",
    "unavailable",
    name="reviewmodulestatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    public_opinion_event_status.create(bind, checkfirst=True)
    platform_rule_status.create(bind, checkfirst=True)
    knowledge_import_job_status.create(bind, checkfirst=True)
    review_module_status.create(bind, checkfirst=True)

    op.create_table(
        "public_opinion_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("consequence_text", sa.Text(), nullable=False),
        sa.Column("source_meta", sa.JSON(), nullable=False),
        sa.Column("status", public_opinion_event_status, nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=False),
        sa.Column("updated_by_id", sa.String(length=36), nullable=True),
        sa.Column("published_by_id", sa.String(length=36), nullable=True),
        sa.Column("archived_by_id", sa.String(length=36), nullable=True),
        sa.Column("restored_by_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["archived_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["published_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["restored_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_public_opinion_events_created_by_id", "public_opinion_events", ["created_by_id"])
    op.create_index("ix_public_opinion_events_external_id", "public_opinion_events", ["external_id"], unique=True)
    op.create_index("ix_public_opinion_events_status", "public_opinion_events", ["status"])

    op.create_table(
        "public_opinion_event_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("industry", sa.JSON(), nullable=False),
        sa.Column("platforms", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("event_process", sa.JSON(), nullable=False),
        sa.Column("consequences", sa.JSON(), nullable=False),
        sa.Column("risk_topics", sa.JSON(), nullable=False),
        sa.Column("trigger_patterns", sa.JSON(), nullable=False),
        sa.Column("affected_groups", sa.JSON(), nullable=False),
        sa.Column("propagation_drivers", sa.JSON(), nullable=False),
        sa.Column("normalized_tags", sa.JSON(), nullable=False),
        sa.Column("severity_level", sa.String(length=20), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edited_by_id", sa.String(length=36), nullable=True),
        sa.Column("edit_notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["edited_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["public_opinion_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "version", name="uq_public_opinion_event_versions_event_version"),
    )
    op.create_index("ix_public_opinion_event_versions_event_id", "public_opinion_event_versions", ["event_id"])

    op.create_table(
        "public_opinion_library_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("event_ids", sa.JSON(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_public_opinion_library_versions_version", "public_opinion_library_versions", ["version"], unique=True)

    op.create_table(
        "platform_rule_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("platform_name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_rule_sets_platform_name", "platform_rule_sets", ["platform_name"], unique=True)

    op.create_table(
        "platform_rule_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("rule_set_id", sa.String(length=36), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("structured_rules", sa.JSON(), nullable=False),
        sa.Column("diff_summary", sa.JSON(), nullable=False),
        sa.Column("status", platform_rule_status, nullable=False),
        sa.Column("imported_by_id", sa.String(length=36), nullable=False),
        sa.Column("reviewed_by_id", sa.String(length=36), nullable=True),
        sa.Column("activated_by_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["activated_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["imported_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rule_set_id"], ["platform_rule_sets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_set_id", "version_label", name="uq_platform_rule_versions_set_label"),
    )
    op.create_index("ix_platform_rule_versions_rule_set_id", "platform_rule_versions", ["rule_set_id"])
    op.create_index("ix_platform_rule_versions_status", "platform_rule_versions", ["status"])

    op.create_table(
        "knowledge_import_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("import_type", sa.String(length=50), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("status", knowledge_import_job_status, nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("valid_items", sa.Integer(), nullable=False),
        sa.Column("invalid_items", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.JSON(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_import_jobs_created_by_id", "knowledge_import_jobs", ["created_by_id"])
    op.create_index("ix_knowledge_import_jobs_import_type", "knowledge_import_jobs", ["import_type"])
    op.create_index("ix_knowledge_import_jobs_status", "knowledge_import_jobs", ["status"])

    op.create_table(
        "knowledge_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=False),
        sa.Column("after_state", sa.JSON(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_audit_logs_action", "knowledge_audit_logs", ["action"])
    op.create_index("ix_knowledge_audit_logs_actor_id", "knowledge_audit_logs", ["actor_id"])
    op.create_index("ix_knowledge_audit_logs_target_id", "knowledge_audit_logs", ["target_id"])
    op.create_index("ix_knowledge_audit_logs_target_type", "knowledge_audit_logs", ["target_type"])

    op.add_column("reviews", sa.Column("legal_library_version_id", sa.String(length=36), nullable=True))
    op.add_column("reviews", sa.Column("industry_library_version_id", sa.String(length=36), nullable=True))
    op.add_column(
        "reviews",
        sa.Column("platform_rule_version_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "reviews",
        sa.Column("public_opinion_library_version_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "reviews",
        sa.Column("legal_module_status", review_module_status, nullable=False, server_default="pending"),
    )
    op.add_column("reviews", sa.Column("legal_module_error", sa.Text(), nullable=True))
    op.add_column(
        "reviews",
        sa.Column("legal_module_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("reviews", sa.Column("legal_module_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "reviews",
        sa.Column("public_opinion_module_status", review_module_status, nullable=False, server_default="pending"),
    )
    op.add_column(
        "reviews",
        sa.Column("public_opinion_result", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column("reviews", sa.Column("public_opinion_module_error", sa.Text(), nullable=True))
    op.add_column(
        "reviews",
        sa.Column("public_opinion_module_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("reviews", sa.Column("public_opinion_module_completed_at", sa.DateTime(timezone=True), nullable=True))
    # Use batch_alter_table for SQLite FK compatibility
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.create_foreign_key(
            "fk_reviews_public_opinion_library_version_id",
            "public_opinion_library_versions",
            ["public_opinion_library_version_id"],
            ["id"],
        )
    op.create_index("ix_reviews_legal_module_status", "reviews", ["legal_module_status"])
    op.create_index("ix_reviews_public_opinion_module_status", "reviews", ["public_opinion_module_status"])


def downgrade() -> None:
    op.drop_index("ix_reviews_public_opinion_module_status", table_name="reviews")
    op.drop_index("ix_reviews_legal_module_status", table_name="reviews")
    op.drop_constraint("fk_reviews_public_opinion_library_version_id", "reviews", type_="foreignkey")
    op.drop_column("reviews", "public_opinion_module_completed_at")
    op.drop_column("reviews", "public_opinion_module_retry_count")
    op.drop_column("reviews", "public_opinion_module_error")
    op.drop_column("reviews", "public_opinion_result")
    op.drop_column("reviews", "public_opinion_module_status")
    op.drop_column("reviews", "legal_module_completed_at")
    op.drop_column("reviews", "legal_module_retry_count")
    op.drop_column("reviews", "legal_module_error")
    op.drop_column("reviews", "legal_module_status")
    op.drop_column("reviews", "public_opinion_library_version_id")
    op.drop_column("reviews", "platform_rule_version_ids")
    op.drop_column("reviews", "industry_library_version_id")
    op.drop_column("reviews", "legal_library_version_id")

    op.drop_index("ix_knowledge_audit_logs_target_type", table_name="knowledge_audit_logs")
    op.drop_index("ix_knowledge_audit_logs_target_id", table_name="knowledge_audit_logs")
    op.drop_index("ix_knowledge_audit_logs_actor_id", table_name="knowledge_audit_logs")
    op.drop_index("ix_knowledge_audit_logs_action", table_name="knowledge_audit_logs")
    op.drop_table("knowledge_audit_logs")

    op.drop_index("ix_knowledge_import_jobs_status", table_name="knowledge_import_jobs")
    op.drop_index("ix_knowledge_import_jobs_import_type", table_name="knowledge_import_jobs")
    op.drop_index("ix_knowledge_import_jobs_created_by_id", table_name="knowledge_import_jobs")
    op.drop_table("knowledge_import_jobs")

    op.drop_index("ix_platform_rule_versions_status", table_name="platform_rule_versions")
    op.drop_index("ix_platform_rule_versions_rule_set_id", table_name="platform_rule_versions")
    op.drop_table("platform_rule_versions")

    op.drop_index("ix_platform_rule_sets_platform_name", table_name="platform_rule_sets")
    op.drop_table("platform_rule_sets")

    op.drop_index("ix_public_opinion_library_versions_version", table_name="public_opinion_library_versions")
    op.drop_table("public_opinion_library_versions")

    op.drop_index("ix_public_opinion_event_versions_event_id", table_name="public_opinion_event_versions")
    op.drop_table("public_opinion_event_versions")

    op.drop_index("ix_public_opinion_events_status", table_name="public_opinion_events")
    op.drop_index("ix_public_opinion_events_external_id", table_name="public_opinion_events")
    op.drop_index("ix_public_opinion_events_created_by_id", table_name="public_opinion_events")
    op.drop_table("public_opinion_events")

    bind = op.get_bind()
    review_module_status.drop(bind, checkfirst=True)
    knowledge_import_job_status.drop(bind, checkfirst=True)
    platform_rule_status.drop(bind, checkfirst=True)
    public_opinion_event_status.drop(bind, checkfirst=True)
