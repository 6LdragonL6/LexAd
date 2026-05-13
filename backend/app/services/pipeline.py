"""审查流程编排器 —— 串联所有子服务，形成完整的广告合规审查流水线。"""

from __future__ import annotations

from fastapi import UploadFile

from app.schemas.models import StandardRequest, StandardResponse
from app.services.case_match import match_cases
from app.services.final_suggestion import generate_final_suggestion
from app.services.penalty import assess_penalty
from app.services.preprocess import run_preprocess
from app.services.review import run_review
from app.services.rule_assembly import assemble_standard_request
from app.services.template_match import match_templates


def run_full_pipeline(
    raw_text: str,
    image_file: UploadFile | None = None,
) -> StandardResponse:
    """执行完整的广告合规审查流程：预处理 → 组装 → 审查 → 案例匹配 → 模板匹配 → 罚金评估 → 最终建议。"""
    # 1. 预处理（文本校验 + 可选 OCR）
    preprocess_result = run_preprocess(raw_text, image_file)

    # 2. 组装标准化请求
    image_filename = image_file.filename if image_file else None
    standard_request = assemble_standard_request(
        raw_text, image_filename, preprocess_result
    )

    # 3. 三层合规审查（法律 / 行业 / 平台）
    review_result = run_review(standard_request)

    # 4. 案例匹配
    case_refs = match_cases(review_result)

    # 5. 模板匹配
    template_refs = match_templates(review_result)

    # 6. 罚金评估
    all_matched = _collect_matched_rule_ids(review_result)
    penalty = assess_penalty(
        risk_level="low" if all_matched else "none", matched_rules=all_matched
    )

    # 7. 生成最终建议
    final = generate_final_suggestion(
        preprocess_result, review_result, case_refs, template_refs, penalty
    )

    return StandardResponse(
        request_id=standard_request.request_id,
        created_at=standard_request.created_at,
        input=standard_request.input,
        preprocess=preprocess_result,
        review=review_result,
        case_references=case_refs,
        rewrite_templates=template_refs,
        penalty_assessment=penalty,
        final_result=final,
    )


def _collect_matched_rule_ids(review) -> list[str]:
    """从三层审查结果中收集所有命中规则的 ID 列表。"""
    ids: list[str] = []
    for layer in [review.legal_review, review.industry_review, review.platform_review]:
        for rule in layer.matched_rules:
            ids.append(rule.rule_id)
    return ids
