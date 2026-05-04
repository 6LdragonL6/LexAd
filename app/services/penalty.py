"""Penalty assessment service: estimates penalties based on risk level and matched rules.

First version returns placeholder assessments only — no real penalty rules.
"""

from __future__ import annotations

from app.schemas.models import PenaltyAssessment


def assess_penalty(risk_level: str, matched_rules: list[str]) -> PenaltyAssessment:
    """Return a mock penalty assessment.

    Args:
        risk_level: Aggregate risk level string.
        matched_rules: List of matched rule IDs.

    Returns:
        PenaltyAssessment with placeholder values.
    """
    # TODO: Replace with real penalty calculation logic.
    #   - Map risk_level to penalty tiers
    #   - Look up fine ranges per matched rule
    #   - Compute aggregate assessment

    if not matched_rules:
        return PenaltyAssessment(
            penalty_level="none",
            penalty_amount="0 元",
            assessment_notes="Mock: 未命中违规规则，无罚金评估。",
        )

    return PenaltyAssessment(
        penalty_level="low",
        penalty_amount="(占位) 待评估",
        assessment_notes="Mock: 此为占位罚金评估。TODO: 接入真实罚金计算逻辑。",
    )
