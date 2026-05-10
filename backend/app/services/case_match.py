"""Case matching service: references similar cases from the case library."""

from __future__ import annotations

from app.core.config import DATA_DIR
from app.schemas.models import CaseReference, ThreeLayerReview
from app.utils.json_reader import read_json_list


def match_cases(review: ThreeLayerReview) -> list[CaseReference]:
    case_file = DATA_DIR / "case_library.json"
    cases_data = read_json_list(case_file)

    if not cases_data:
        return []

    results: list[CaseReference] = []
    for item in cases_data:
        results.append(CaseReference(
            case_id=item.get("case_id", ""),
            title=item.get("title", ""),
            similarity=0.0,
            relevance="",
            summary=item.get("summary", ""),
        ))
    return results
