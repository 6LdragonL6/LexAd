"""罚金评估服务 —— 根据风险等级和命中规则估算罚金。"""

from __future__ import annotations

from app.schemas.models import PenaltyAssessment


def assess_penalty(risk_level: str, matched_rules: list[str]) -> PenaltyAssessment:
    """根据风险等级和命中规则列表评估罚金等级与金额。当前为 Mock 占位。"""
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
