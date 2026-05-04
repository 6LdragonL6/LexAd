"""Review service: runs three-layer compliance review (legal, industry, platform).

First version returns mock/placeholder results.  Each layer has complete field structure.
"""

from __future__ import annotations

from app.schemas.models import (
    MatchedRule,
    SingleLayerReview,
    StandardRequest,
    ThreeLayerReview,
)


def run_review(request: StandardRequest) -> ThreeLayerReview:
    """Execute the three-layer compliance review.

    Args:
        request: Standardized review request from rule_assembly service.

    Returns:
        ThreeLayerReview with legal, industry, and platform sub-reviews.
    """
    has_text = bool(request.input.raw_text.strip())

    # TODO: Replace mock with real rule engine.  Match against:
    #   - data/legal_rules.json
    #   - data/industry_rules.json
    #   - data/platform_rules.json

    return ThreeLayerReview(
        legal_review=SingleLayerReview(
            level="legal",
            status="pass" if has_text else "pending",
            risk_score=0,
            matched_rules=[],
            explanations=[
                "Mock: 未匹配到法律层面违规规则。"
                if has_text
                else "Mock: 无文本输入，跳过法律审查。"
            ],
            suggestions=[
                "TODO: 接入真实法律法规库后可输出具体建议。"
            ],
        ),
        industry_review=SingleLayerReview(
            level="industry",
            status="pass" if has_text else "pending",
            risk_score=0,
            matched_rules=[],
            explanations=[
                "Mock: 未匹配到行业层面违规规则。"
                if has_text
                else "Mock: 无文本输入，跳过行业审查。"
            ],
            suggestions=[
                "TODO: 接入真实行业规范库后可输出具体建议。"
            ],
        ),
        platform_review=SingleLayerReview(
            level="platform",
            status="pass" if has_text else "pending",
            risk_score=0,
            matched_rules=[],
            explanations=[
                "Mock: 未匹配到平台层面违规规则。"
                if has_text
                else "Mock: 无文本输入，跳过平台审查。"
            ],
            suggestions=[
                "TODO: 接入真实平台规则库后可输出具体建议。"
            ],
        ),
    )
