from app.schemas.review import EngineResult, LayerResult, MatchedRule
from app.engine.layer1_hard_rules import engine_l1


def run_review_pipeline(raw_text: str, industry: str, platforms: list[str]) -> EngineResult:
    # L1: Hard rules
    l1_result = engine_l1.scan(raw_text)

    # L2: Semantic (DeepSeek)
    from app.engine.layer2_semantic import run_semantic_review
    l2_result = run_semantic_review(raw_text, industry)

    # L3: Evidence check (stub — full implementation in Phase 2)
    evidence_patterns = ["经临床验证", "实验表明", "数据显示", "调查显示", "获认证", "通过检测", "经XX验证", "临床证明"]
    evidence_matched = []
    for pattern in evidence_patterns:
        if pattern in raw_text:
            evidence_matched.append(MatchedRule(
                rule_id=f"L3-{hash(pattern) & 0xFFFFFFFF:08x}",
                rule_text=pattern,
                source_law="《广告法》第28条",
                match_type="需证明材料",
            ))
    l3_result = LayerResult(
        layer="第三层·证明材料检查",
        matched_rules=evidence_matched,
        explanations=[f"发现 {len(evidence_matched)} 处需证明材料支撑的表述"] if evidence_matched else ["无需证明材料的表述"],
    )

    # L4: Platform adapt (stub — full implementation in Phase 2)
    l4_result = LayerResult(
        layer="第四层·平台差异适配",
        matched_rules=[],
        explanations=[f"目标平台: {', '.join(platforms)} — 平台差异适配将在第二阶段实现"],
    )

    # Score: 100 - deductions
    deduction_map = {
        "绝对化用语": 30, "涉医用语": 35, "功效宣称": 25, "效果保证": 20,
        "价格欺诈": 20, "权威背书": 15, "虚假表述": 15, "迷信内容": 25,
        "high": 30, "medium": 20, "low": 10, "需证明材料": 5,
    }
    total_deduction = 0
    for result in [l1_result, l2_result, l3_result]:
        for rule in result.matched_rules:
            total_deduction += deduction_map.get(rule.match_type, 15)

    risk_score = max(0, 100 - total_deduction)

    # Summary
    all_violations = []
    for result in [l1_result, l2_result, l3_result]:
        for rule in result.matched_rules:
            all_violations.append(f"· {rule.match_type}: {rule.rule_text}")

    summary_lines = [f"审查完成，风险评分 {risk_score}/100", f"共发现 {len(all_violations)} 项问题"]
    if risk_score >= 80:
        summary_lines.append("评估：低风险，建议通过")
    elif risk_score >= 50:
        summary_lines.append("评估：中风险，建议修改后提交法务审核")
    else:
        summary_lines.append("评估：高风险，强烈建议修改后重新提交")

    suggestions = [f"建议修改: {v.rule_text}" for v in l1_result.matched_rules[:3]]
    suggestions.extend([f"语义问题: {v.rule_text}" for v in l2_result.matched_rules[:3]])

    return EngineResult(
        risk_score=risk_score,
        layer1=l1_result,
        layer2=l2_result,
        layer3=l3_result,
        layer4=l4_result,
        summary="\n".join(summary_lines),
        suggestions=suggestions,
        case_refs=[],
    )
