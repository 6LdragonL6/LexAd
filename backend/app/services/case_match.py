"""案例匹配服务 —— 从案例库中查找相似历史案例。"""

from __future__ import annotations

from app.core.config import DATA_DIR
from app.schemas.models import CaseReference, ThreeLayerReview
from app.utils.json_reader import read_json_list


def match_cases(review: ThreeLayerReview) -> list[CaseReference]:
    """根据三层审查结果从案例库匹配相关案例引用。当前为 Mock 实现。"""
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
