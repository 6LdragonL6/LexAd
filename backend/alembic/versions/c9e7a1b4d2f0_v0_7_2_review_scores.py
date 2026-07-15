"""v0.7.2 explicit legal and public-opinion scores

Revision ID: c9e7a1b4d2f0
Revises: b8d4e1f7a203
Create Date: 2026-07-15
"""

from __future__ import annotations

from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9e7a1b4d2f0"
down_revision: Union[str, None] = "b8d4e1f7a203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


reviews = sa.table(
    "reviews",
    sa.column("id", sa.String(36)),
    sa.column("public_opinion_module_status", sa.String(20)),
    sa.column("public_opinion_result", sa.JSON()),
    sa.column("public_opinion_safety_score", sa.Integer()),
)


def _clean_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    cleaned = dict(value)
    cleaned.pop("risk_score", None)
    cleaned.pop("safety_score", None)
    return cleaned


def _legacy_safety_score(status: str | None, result: Any) -> int | None:
    if status != "succeeded" or not isinstance(result, dict):
        return None
    if result.get("status") == "manual_review" or result.get("requires_manual_review"):
        return None
    legacy = result.get("risk_score")
    if isinstance(legacy, bool) or not isinstance(legacy, (int, float)):
        return None
    return 100 - max(0, min(int(legacy), 100))


def _migrate_public_opinion_results(*, downgrade: bool = False) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            reviews.c.id,
            reviews.c.public_opinion_module_status,
            reviews.c.public_opinion_result,
            reviews.c.public_opinion_safety_score,
        )
    ).mappings()
    for row in rows:
        result = row["public_opinion_result"] if isinstance(row["public_opinion_result"], dict) else {}
        if downgrade:
            restored = dict(result)
            safety_score = row["public_opinion_safety_score"]
            restored["risk_score"] = 100 - int(safety_score) if safety_score is not None else 0
            values = {"public_opinion_result": restored}
        else:
            values = {
                "public_opinion_safety_score": _legacy_safety_score(
                    row["public_opinion_module_status"], result
                ),
                "public_opinion_result": _clean_result(result),
            }
        bind.execute(sa.update(reviews).where(reviews.c.id == row["id"]).values(**values))


def upgrade() -> None:
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.alter_column(
            "ai_risk_score",
            new_column_name="legal_compliance_score",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column("public_opinion_safety_score", sa.Integer(), nullable=True))

    _migrate_public_opinion_results()

    with op.batch_alter_table("reviews") as batch_op:
        batch_op.create_check_constraint(
            "ck_reviews_legal_compliance_score_range",
            "legal_compliance_score >= 0 AND legal_compliance_score <= 100",
        )
        batch_op.create_check_constraint(
            "ck_reviews_public_opinion_safety_score_range",
            "public_opinion_safety_score IS NULL OR "
            "(public_opinion_safety_score >= 0 AND public_opinion_safety_score <= 100)",
        )


def downgrade() -> None:
    _migrate_public_opinion_results(downgrade=True)

    with op.batch_alter_table("reviews") as batch_op:
        batch_op.drop_constraint("ck_reviews_public_opinion_safety_score_range", type_="check")
        batch_op.drop_constraint("ck_reviews_legal_compliance_score_range", type_="check")
        batch_op.drop_column("public_opinion_safety_score")
        batch_op.alter_column(
            "legal_compliance_score",
            new_column_name="ai_risk_score",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
