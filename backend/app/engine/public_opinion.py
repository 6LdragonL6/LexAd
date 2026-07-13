from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.engine.industry import split_industries
from app.models.knowledge import (
    PublicOpinionEvent,
    PublicOpinionEventStatus,
    PublicOpinionEventVersion,
    PublicOpinionLibraryVersion,
)
from app.services import model_service
from app.engine.text_similarity import shared_phrase, similarity

_TRIGGER_WORDS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "trigger_words.json"


def _load_trigger_words() -> dict[str, list[str]]:
    if not _TRIGGER_WORDS_PATH.exists():
        return {}
    try:
        data = json.loads(_TRIGGER_WORDS_PATH.read_text(encoding="utf-8"))
        return data.get("triggers", {})
    except (json.JSONDecodeError, OSError):
        return {}


@dataclass
class PublicOpinionReview:
    status: str
    result: dict[str, Any]
    library_version_id: str | None = None
    error: str | None = None


def run_public_opinion_review(
    *,
    material_text: str,
    industry: str,
    platforms: list[str],
    db: Session,
) -> PublicOpinionReview:
    library_version = _latest_library_version(db)
    if not library_version or library_version.event_count == 0:
        return PublicOpinionReview(
            status="unavailable",
            library_version_id=library_version.id if library_version else None,
            result={
                "status": "knowledge_base_empty",
                "risk_level": "unavailable",
                "message": "舆情资料库待补充，暂无法完成基于案例的舆情判断",
                "similar_events": [],
                "deterministic_hits": [],
                "suggestions": ["请管理员先发布舆情案例，再启用案例化舆情判断"],
            },
        )

    cases = _load_published_cases(db, library_version)
    if not cases:
        return PublicOpinionReview(
            status="unavailable",
            library_version_id=library_version.id,
            result={
                "status": "knowledge_base_empty",
                "risk_level": "unavailable",
                "message": "当前舆情资料库快照中没有可用案例",
                "similar_events": [],
                "deterministic_hits": [],
                "suggestions": ["请管理员检查舆情案例发布状态"],
            },
        )

    deterministic_hits = _deterministic_hits(material_text, industry, platforms, cases)
    trigger_word_hits = _trigger_word_hits(material_text)
    similar_events = _similar_events(deterministic_hits, cases)
    fallback_result = _fallback_result(deterministic_hits, similar_events, trigger_word_hits)

    try:
        model_result = model_service.explain_public_opinion_risk(
            material_text=material_text,
            deterministic_hits=deterministic_hits,
            similar_events=similar_events,
        )
        result = {
            **fallback_result,
            **model_result,
            "status": "succeeded",
            "similar_events": similar_events,
            "deterministic_hits": deterministic_hits,
            "trigger_word_hits": trigger_word_hits,
            "model_available": True,
            "library_version_id": library_version.id,
            "library_version": library_version.version,
        }
    except model_service.ModelServiceError as exc:
        result = {
            **fallback_result,
            "status": "model_unavailable" if (similar_events or deterministic_hits or trigger_word_hits) else "uncertain",
            "model_available": False,
            "model_error": str(exc)[:200],
            "library_version_id": library_version.id,
            "library_version": library_version.version,
            "trigger_word_hits": trigger_word_hits,
        }

    return PublicOpinionReview(
        status="succeeded",
        library_version_id=library_version.id,
        result=result,
    )


def _latest_library_version(db: Session) -> PublicOpinionLibraryVersion | None:
    return (
        db.query(PublicOpinionLibraryVersion)
        .order_by(PublicOpinionLibraryVersion.version.desc(), PublicOpinionLibraryVersion.published_at.desc())
        .first()
    )


def _load_published_cases(
    db: Session,
    library_version: PublicOpinionLibraryVersion,
) -> list[dict[str, Any]]:
    event_ids = library_version.event_ids or []
    if not event_ids:
        return []
    events = (
        db.query(PublicOpinionEvent)
        .filter(
            PublicOpinionEvent.id.in_(event_ids),
            PublicOpinionEvent.status == PublicOpinionEventStatus.published,
        )
        .all()
    )
    cases = []
    for event in events:
        version = (
            db.query(PublicOpinionEventVersion)
            .filter(PublicOpinionEventVersion.event_id == event.id)
            .order_by(PublicOpinionEventVersion.version.desc())
            .first()
        )
        if not version:
            continue
        cases.append({"event": event, "version": version})
    return cases


def _deterministic_hits(
    material_text: str,
    industry: str,
    platforms: list[str],
    cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hits = []
    normalized_platforms = {_normalize(platform) for platform in platforms}
    normalized_industries = {_normalize(item) for item in split_industries(industry)}

    for case in cases:
        event: PublicOpinionEvent = case["event"]
        version: PublicOpinionEventVersion = case["version"]
        tokens = _case_tokens(version)
        matched_tokens = [token for token in tokens if token and token in material_text]
        case_text = " ".join([
            version.source_text,
            version.summary,
            " ".join(version.trigger_patterns or []),
            " ".join(version.risk_topics or []),
        ])
        similarity_score = similarity(material_text, case_text)
        matched_phrase = shared_phrase(material_text, case_text)
        industry_bonus = bool(normalized_industries & {_normalize(item) for item in version.industry})
        platform_bonus = bool(normalized_platforms & {_normalize(item) for item in version.platforms})
        contextual_match = industry_bonus or platform_bonus
        if not matched_tokens and (similarity_score < 0.18 or len(matched_phrase) < 2) and not contextual_match:
            continue
        score = len(matched_tokens) * 20
        if similarity_score >= 0.18 and len(matched_phrase) >= 2:
            score += int(similarity_score * 60)
        if industry_bonus:
            score += 10
        if platform_bonus:
            score += 10
        hits.append(
            {
                "event_id": event.id,
                "event_title": event.title or version.title,
                "matched_tokens": matched_tokens,
                "risk_topics": version.risk_topics,
                "affected_groups": version.affected_groups,
                "propagation_drivers": version.propagation_drivers,
                "historical_consequence": version.consequences,
                "severity_level": version.severity_level,
                "score": min(score, 100),
                "match_method": "keyword" if matched_tokens else ("similarity" if matched_phrase else "context"),
                "matched_text": ", ".join(matched_tokens) or matched_phrase,
            }
        )
    return sorted(hits, key=lambda item: item["score"], reverse=True)


def _similar_events(
    deterministic_hits: list[dict[str, Any]],
    cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if deterministic_hits:
        source = deterministic_hits[:5]
        return [
            {
                "event_id": hit["event_id"],
                "title": hit["event_title"],
                "similarity": hit["score"],
                "severity_level": hit["severity_level"],
                "historical_consequence": hit["historical_consequence"],
            }
            for hit in source
        ]

    return [
        {
            "event_id": case["event"].id,
            "title": case["event"].title or case["version"].title,
            "similarity": 0,
            "severity_level": case["version"].severity_level,
            "historical_consequence": case["version"].consequences,
        }
        for case in cases[:3]
    ]


def _fallback_result(
    deterministic_hits: list[dict[str, Any]],
    similar_events: list[dict[str, Any]],
    trigger_word_hits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    trigger_word_hits = trigger_word_hits or []

    if not deterministic_hits and not trigger_word_hits:
        return {
            "risk_level": "uncertain",
            "risk_topics": [],
            "affected_groups": [],
            "propagation_drivers": [],
            "similar_events": similar_events,
            "deterministic_hits": [],
            "trigger_word_hits": [],
            "suggestions": ["当前物料未命中已发布舆情案例的明确触发因素，建议人工复核敏感表达"],
            "explanation": "资料库有案例，但当前物料缺少足够相似依据，不能直接判断为低风险。",
            "confidence": 20,
        }

    # Merge trigger hits into risk assessment
    trigger_categories = list({h["category"] for h in trigger_word_hits})
    trigger_risk_topics = _dedupe(
        trigger_categories
        + _flatten(hit.get("risk_topics", []) for hit in deterministic_hits)
    )

    all_suggestions = ["建议品牌负责人复核舆情触发点，并参考相似历史事件的后果"]
    if trigger_word_hits:
        matched_words = [h["matched_word"] for h in trigger_word_hits]
        all_suggestions.append(
            f"触发词命中：{', '.join(matched_words[:5])}，请核实是否构成舆情风险"
        )

    if not deterministic_hits:
        # Only trigger word hits, no case matches
        trigger_confidence = min(len(trigger_word_hits) * 15, 60)
        return {
            "risk_level": "medium" if len(trigger_word_hits) >= 2 else "low",
            "risk_topics": trigger_risk_topics,
            "affected_groups": [],
            "propagation_drivers": [],
            "similar_events": similar_events,
            "deterministic_hits": [],
            "trigger_word_hits": trigger_word_hits,
            "suggestions": all_suggestions,
            "explanation": f"物料命中 {len(trigger_word_hits)} 个触发词但未匹配历史案例，建议人工判定。",
            "confidence": trigger_confidence,
        }

    max_score = max(hit["score"] for hit in deterministic_hits)
    # Boost score based on trigger word matches
    trigger_boost = min(len(trigger_word_hits) * 10, 30)
    adjusted_score = min(max_score + trigger_boost, 100)

    severities = {str(hit.get("severity_level") or "").lower() for hit in deterministic_hits}
    if adjusted_score >= 80 or ("severe" in severities and adjusted_score >= 40):
        risk_level = "severe"
    elif adjusted_score >= 60 or ("high" in severities and adjusted_score >= 40):
        risk_level = "high"
    elif adjusted_score >= 30 or ("medium" in severities and adjusted_score >= 25):
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_topics": trigger_risk_topics,
        "affected_groups": _dedupe(_flatten(hit.get("affected_groups", []) for hit in deterministic_hits)),
        "propagation_drivers": _dedupe(_flatten(hit.get("propagation_drivers", []) for hit in deterministic_hits)),
        "similar_events": similar_events,
        "deterministic_hits": deterministic_hits,
        "trigger_word_hits": trigger_word_hits,
        "suggestions": all_suggestions,
        "explanation": "物料命中已发布舆情案例中的触发因素或触发词，建议人工复核。",
        "confidence": min(adjusted_score, 90),
    }


def _case_tokens(version: PublicOpinionEventVersion) -> list[str]:
    tokens = []
    tokens.extend(_string_list(version.trigger_patterns))
    tokens.extend(_string_list(version.risk_topics))
    tokens.extend(_string_list(version.affected_groups))
    event_process = version.event_process or {}
    trigger = event_process.get("trigger")
    if isinstance(trigger, str) and len(trigger.strip()) <= 30:
        tokens.append(trigger.strip())
    return _dedupe([token for token in tokens if 1 < len(token) <= 30])


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _flatten(groups) -> list[str]:
    flattened: list[str] = []
    for group in groups:
        flattened.extend(_string_list(group))
    return flattened


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _trigger_word_hits(material_text: str) -> list[dict[str, Any]]:
    triggers = _load_trigger_words()
    hits: list[dict[str, Any]] = []
    for category, words in triggers.items():
        for word in words:
            if word in material_text:
                hits.append({"category": category, "matched_word": word})
    return hits


def _normalize(value: str) -> str:
    return "".join(str(value or "").lower().split())
