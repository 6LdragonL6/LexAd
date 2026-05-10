"""Penalty assessment service: estimates penalties based on risk level and matched rules."""

from __future__ import annotations

from app.schemas.models import PenaltyAssessment


def assess_penalty(risk_level: str, matched_rules: list[str]) -> PenaltyAssessment:
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
