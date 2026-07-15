from __future__ import annotations

from typing import Any


_LABELS = {
    "accepted": "物料已接收",
    "legal_review": "法规审核",
    "public_opinion_review": "舆情审核",
    "finalizing": "汇总审查结果",
}


def _module_stage(status: str | None, result: dict[str, Any]) -> str:
    normalized = status or "pending"
    if normalized == "pending":
        return "pending"
    if normalized == "running":
        return "running"
    if normalized == "failed":
        return "failed"
    if normalized == "unavailable":
        return "manual_review"
    if normalized == "succeeded":
        if result.get("review_status") == "manual_review":
            return "manual_review"
        if result.get("status") == "manual_review" or result.get("requires_manual_review"):
            return "manual_review"
        return "completed"
    return "pending"


def build_review_stages(
    *,
    task_status: str,
    legal_module_status: str | None,
    public_opinion_module_status: str | None,
    ai_result: dict[str, Any] | None,
    public_opinion_result: dict[str, Any] | None,
) -> list[dict[str, str]]:
    legal = _module_stage(legal_module_status, ai_result or {})
    public_opinion = _module_stage(public_opinion_module_status, public_opinion_result or {})
    terminal = {"completed", "manual_review", "failed"}

    if task_status == "failed":
        finalizing = "failed"
    elif task_status == "completed":
        finalizing = "completed"
    elif legal in terminal and public_opinion in terminal:
        finalizing = "running"
    else:
        finalizing = "pending"

    states = {
        "accepted": "completed",
        "legal_review": legal,
        "public_opinion_review": public_opinion,
        "finalizing": finalizing,
    }
    return [
        {"key": key, "label": _LABELS[key], "status": states[key]}
        for key in ("accepted", "legal_review", "public_opinion_review", "finalizing")
    ]
