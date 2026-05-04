"""Case matching service: references similar cases from the case library.

First version reads from data/case_library.json if available, returns empty otherwise.
"""

from __future__ import annotations

from app.core.config import DATA_DIR
from app.schemas.models import CaseReference, ThreeLayerReview
from app.utils.json_reader import read_json_list


def match_cases(review: ThreeLayerReview) -> list[CaseReference]:
    """Find matching cases from the case library.

    Args:
        review: Three-layer review result.

    Returns:
        List of CaseReference entries (empty in first version).
    """
    case_file = DATA_DIR / "case_library.json"
    cases_data = read_json_list(case_file)

    if not cases_data:
        return []

    # TODO: Implement real case matching logic (e.g. embedding similarity,
    #   keyword overlap, rule-based matching).
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
