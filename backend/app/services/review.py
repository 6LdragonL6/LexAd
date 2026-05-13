"""审查服务 —— 执行法律、行业、平台三层合规审查（当前为 Mock 占位）。"""

from __future__ import annotations

from app.schemas.models import (
    MatchedRule,
    SingleLayerReview,
    StandardRequest,
    ThreeLayerReview,
)


def run_review(request: StandardRequest) -> ThreeLayerReview:
    """对标准化请求执行三层合规审查，返回各层级的审查结果。当前为 Mock 实现。"""
    has_text = bool(request.input.raw_text.strip())

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
            suggestions=["TODO: 接入真实法律法规库后可输出具体建议。"],
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
            suggestions=["TODO: 接入真实行业规范库后可输出具体建议。"],
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
            suggestions=["TODO: 接入真实平台规则库后可输出具体建议。"],
        ),
    )
