from sqlalchemy.orm import Session

from app.engine.layer1_hard_rules import engine_l1
from app.engine.layer4_platform import run_platform_adjudication
from app.schemas.review import EngineResult, LayerResult, MatchedRule


_DEDUCTION_BY_LEVEL = {"high": 30, "medium": 15, "low": 5}


def run_review_pipeline(
    raw_text: str,
    industry: str,
    platforms: list[str],
    db: Session | None = None,
) -> EngineResult:
    # Deterministic rules are recall-only candidates in v0.7.0.
    hard_candidates = engine_l1.scan(raw_text).matched_rules
    l1_result = LayerResult(
        layer="规则候选召回",
        matched_rules=[],
        explanations=["规则候选已提供给 AI 结合完整语境裁决，候选本身不代表违规"],
        status="no_match",
        candidate_count=len(hard_candidates),
    )

    from app.engine.layer2_semantic import SemanticReviewError, run_semantic_review

    try:
        l2_result = run_semantic_review(raw_text, industry, db, hard_candidates)
    except SemanticReviewError as exc:
        l2_result = LayerResult(
            layer="法律语义裁决",
            status="unavailable",
            explanations=[str(exc)[:200] or "AI 法律裁决暂不可用，当前结果需人工复核"],
            candidate_count=len(hard_candidates),
            requires_manual_review=True,
        )

    l4_result = run_platform_adjudication(raw_text, platforms, db)
    verification_items = [*l2_result.verification_items, *l4_result.verification_items]
    l3_result = LayerResult(
        layer="资料核验事项",
        matched_rules=[],
        verification_items=verification_items,
        explanations=(
            [f"发现 {len(verification_items)} 项事实、来源、资质或证明材料需要核验"]
            if verification_items
            else ["未发现需要补充核验的资料事项"]
        ),
        status="matched" if verification_items else "no_match",
    )

    confirmed = _dedupe_findings([*l2_result.matched_rules, *l4_result.matched_rules])
    total_deduction = sum(_DEDUCTION_BY_LEVEL.get(item.risk_level, 15) for item in confirmed)
    compliance_score = max(0, 100 - min(total_deduction, 100))
    requires_manual_review = l2_result.requires_manual_review or l4_result.requires_manual_review

    if requires_manual_review:
        review_status = "manual_review"
        recommendation = "部分审查依据不足或 AI 裁决不可用，需人工复核"
    elif confirmed:
        review_status = "confirmed_risk"
        recommendation = "发现已确认风险，建议修改后提交法务审核"
    elif verification_items:
        review_status = "needs_verification"
        recommendation = "未发现明确违规，建议补充或核验资料后通过"
    else:
        review_status = "no_clear_risk"
        recommendation = "未发现明确风险，仍建议按实际投放场景复核"

    summary_lines = [
        f"法律合规评分 {compliance_score}/100",
        f"已确认 {len(confirmed)} 项风险，{len(verification_items)} 项资料待核验",
        recommendation,
    ]
    suggestions = [item.suggestion for item in confirmed if item.suggestion][:8]
    if verification_items:
        suggestions.append("请补充并核验相关数据来源、统计口径、资质或证明材料")

    return EngineResult(
        compliance_score=compliance_score,
        layer1=l1_result,
        layer2=l2_result,
        layer3=l3_result,
        layer4=l4_result,
        summary="\n".join(summary_lines),
        suggestions=suggestions,
        case_refs=[],
        platform_rule_version_ids=l4_result.platform_rule_version_ids,
        unavailable_platforms=l4_result.unavailable_platforms,
        platform_version_labels=l4_result.platform_version_labels,
        hit_count=len(confirmed),
        risk_topics=list(dict.fromkeys(item.match_type for item in confirmed)),
        verification_items=verification_items,
        requires_manual_review=requires_manual_review,
        review_status=review_status,
    )


def _dedupe_findings(findings: list[MatchedRule]) -> list[MatchedRule]:
    seen: set[tuple[str, str]] = set()
    result: list[MatchedRule] = []
    for finding in findings:
        evidence = "".join((finding.evidence_quote or finding.rule_text).lower().split())
        risk_type = "".join(finding.match_type.lower().split())
        key = (evidence, risk_type)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result
