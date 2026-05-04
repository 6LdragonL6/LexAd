"""Final suggestion service: generates overall recommendations from all analysis results.

First version returns mock/placeholder — no deep conclusions.
"""

from __future__ import annotations

from app.schemas.models import (
    CaseReference,
    FinalResult,
    PenaltyAssessment,
    PreprocessResult,
    RewriteTemplate,
    ThreeLayerReview,
)


def generate_final_suggestion(
    preprocess: PreprocessResult,
    review: ThreeLayerReview,
    cases: list[CaseReference],
    templates: list[RewriteTemplate],
    penalty: PenaltyAssessment,
) -> FinalResult:
    """Generate a final summary and recommendations.

    Args:
        preprocess: Preprocess result.
        review: Three-layer review result.
        cases: Matched case references.
        templates: Matched rewrite templates.
        penalty: Penalty assessment.

    Returns:
        FinalResult with overall status, summary, recommendations, and notes.
    """
    # TODO: Replace mock with real synthesis logic once rule engine is implemented.

    warnings_count = len(preprocess.warnings)

    return FinalResult(
        overall_status="pass",
        summary=(
            "Mock 最终结论：当前广告文案未命中违规规则。"
            if not warnings_count
            else f"Mock 最终结论：审查完成，有 {warnings_count} 条提示信息。"
        ),
        recommendations=[
            "TODO: 接入真实审查引擎后可给出具体修改建议。",
            "TODO: 参考案例库和模板库进行文案优化。",
        ],
        notes=(
            "本结论为 Demo 占位结果，不构成真实审查意见。"
            "请勿用于正式合规判断。"
            "案例命中数: %d，模板命中数: %d，罚金等级: %s。"
            % (len(cases), len(templates), penalty.penalty_level)
        ),
    )
