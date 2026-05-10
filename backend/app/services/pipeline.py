"""Pipeline orchestrator: wires together all services into a single review flow."""

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
    # 1. Preprocess
    preprocess_result = run_preprocess(raw_text, image_file)

    # 2. Assemble standard request
    image_filename = image_file.filename if image_file else None
    standard_request = assemble_standard_request(
        raw_text, image_filename, preprocess_result
    )

    # 3. Three-layer review
    review_result = run_review(standard_request)

    # 4. Case matching
    case_refs = match_cases(review_result)

    # 5. Template matching
    template_refs = match_templates(review_result)

    # 6. Penalty assessment
    all_matched = _collect_matched_rule_ids(review_result)
    penalty = assess_penalty(
        risk_level="low" if all_matched else "none", matched_rules=all_matched
    )

    # 7. Final suggestion
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
    ids: list[str] = []
    for layer in [review.legal_review, review.industry_review, review.platform_review]:
        for rule in layer.matched_rules:
            ids.append(rule.rule_id)
    return ids
