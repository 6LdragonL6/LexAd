from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.engine.industry import split_industries
from app.engine.text_similarity import char_ngrams, normalize_text, shared_phrase, similarity
from app.models.knowledge import (
    PublicOpinionEvent,
    PublicOpinionEventStatus,
    PublicOpinionEventVersion,
    PublicOpinionLibraryVersion,
)
from app.services import model_service


_TRIGGER_WORDS_PATH = Path(__file__).resolve().parents[3] / "data" / "trigger_words.json"
_SAFETY_SCORES = {"low": 85, "medium": 70, "high": 40, "severe": 10, "uncertain": 0}
_SAFETY_RANGES = {
    "low": (80, 100),
    "medium": (60, 79),
    "high": (20, 59),
    "severe": (0, 19),
    "uncertain": (0, 0),
}
_GENERIC_BIGRAMS = {"这个", "一种", "可以", "可能", "我们", "你们", "他们", "没有", "不是", "广告", "文案"}


@dataclass
class PublicOpinionReview:
    status: str
    result: dict[str, Any]
    safety_score: int | None = None
    library_version_id: str | None = None
    error: str | None = None


def run_public_opinion_review(
    *,
    material_text: str,
    industry: str,
    platforms: list[str],
    db: Session,
) -> PublicOpinionReview:
    trigger_word_hits = _trigger_word_hits(material_text)
    library_version = _latest_library_version(db)
    cases = _load_published_cases(db, library_version) if library_version else []
    deterministic_hits = _deterministic_hits(
        material_text,
        industry,
        platforms,
        cases,
        trigger_word_hits,
    )
    candidate_events = _similar_events(deterministic_hits)

    model_error: str | None = None
    try:
        model_result = model_service.explain_public_opinion_risk(
            db=db,
            material_text=material_text,
            deterministic_hits=deterministic_hits,
            similar_events=candidate_events,
            trigger_word_hits=trigger_word_hits,
        )
        ai = _validated_ai_assessment(material_text, model_result, candidate_events)
        result = _ai_only_result(ai)
        selected_events = _selected_similar_events(candidate_events, ai.get("matched_case_ids", []))
        model_available = True
    except model_service.ModelServiceError as exc:
        model_error = str(exc)[:200]
        result = _manual_review_result("AI 舆情裁决暂不可用，候选词条和案例不能替代语义判断")
        selected_events = []
        model_available = False

    safety_score = result.pop("safety_score", None)
    result.update({
        "status": "succeeded" if model_available and not result.get("requires_manual_review") else "manual_review",
        "model_available": model_available,
        "model_error": model_error,
        "similar_events": selected_events,
        "library_version_id": library_version.id if library_version else None,
        "library_version": library_version.version if library_version else None,
        "knowledge_base_available": bool(cases),
    })
    return PublicOpinionReview(
        status="succeeded",
        library_version_id=library_version.id if library_version else None,
        result=result,
        safety_score=safety_score,
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
            PublicOpinionEvent.deleted_at.is_(None),
        )
        .all()
    )
    cases: list[dict[str, Any]] = []
    for event in events:
        version = (
            db.query(PublicOpinionEventVersion)
            .filter(PublicOpinionEventVersion.event_id == event.id)
            .order_by(PublicOpinionEventVersion.version.desc())
            .first()
        )
        if version:
            cases.append({"event": event, "version": version})
    return cases


def _deterministic_hits(
    material_text: str,
    industry: str,
    platforms: list[str],
    cases: list[dict[str, Any]],
    trigger_word_hits: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    trigger_word_hits = trigger_word_hits or []
    normalized_platforms = {_normalize(platform) for platform in platforms}
    normalized_industries = {_normalize(item) for item in split_industries(industry)}
    trigger_words = {str(hit["matched_word"]) for hit in trigger_word_hits}
    trigger_categories = {str(hit["category"]) for hit in trigger_word_hits}
    material_grams = char_ngrams(material_text)

    for case in cases:
        event: PublicOpinionEvent = case["event"]
        version: PublicOpinionEventVersion = case["version"]
        segments = _case_segments(event, version)
        case_text = " ".join(segments)
        tokens = _case_tokens(version)
        exact_tokens = [token for token in tokens if token and token in material_text]
        case_trigger_words = sorted(word for word in trigger_words if word and word in case_text)
        topic_match = _topic_matches(trigger_categories, version.risk_topics or [])
        segment_similarity = max((similarity(material_text, segment) for segment in segments if segment), default=0.0)
        phrase = shared_phrase(material_text, case_text)
        common_grams = sorted(
            gram
            for gram in material_grams & char_ngrams(case_text)
            if gram not in _GENERIC_BIGRAMS and gram not in trigger_words
        )
        context_evidence = bool(exact_tokens or len(phrase) >= 4 or segment_similarity >= 0.12 or common_grams)
        if not context_evidence:
            continue

        industry_bonus = bool(normalized_industries & {_normalize(item) for item in version.industry or []})
        platform_bonus = bool(normalized_platforms & {_normalize(item) for item in version.platforms or []})
        score = 0
        if exact_tokens:
            score += min(60 + (len(exact_tokens) - 1) * 8, 76)
        score += min(len(case_trigger_words) * 18, 36)
        score += min(len(common_grams) * 8, 24)
        score += int(segment_similarity * 70)
        score += min(len(phrase) * 2, 16) if len(phrase) >= 4 else 0
        score += 10 if topic_match else 0
        score += 8 if industry_bonus else 0
        score += 5 if platform_bonus else 0
        score = min(score, 100)
        if score < 20:
            continue
        source_meta = event.source_meta if isinstance(event.source_meta, dict) else {}
        verification = source_meta.get("verification") if isinstance(source_meta.get("verification"), dict) else {}
        verification_status = str(
            verification.get("verdict")
            or (version.normalized_tags or {}).get("verification_verdict")
            or ""
        )
        base_confidence = float(version.confidence or 50) / 100
        confidence = min(0.95, max(0.30, (score / 100 * 0.65) + (base_confidence * 0.35)))
        hits.append({
            "event_id": event.id,
            "external_id": event.external_id,
            "event_title": event.title or version.title,
            "matched_tokens": _dedupe([*exact_tokens, *case_trigger_words]),
            "risk_topics": version.risk_topics or [],
            "affected_groups": version.affected_groups or [],
            "propagation_drivers": version.propagation_drivers or [],
            "historical_consequence": version.consequences or {},
            "severity_level": version.severity_level,
            "verification_status": verification_status,
            "sources": (version.sources or [])[:5],
            "score": score,
            "confidence": round(confidence, 3),
            "match_method": "exact" if exact_tokens else "hybrid_similarity",
            "matched_text": ", ".join(_dedupe([*exact_tokens, *case_trigger_words, *common_grams[:4]])) or phrase,
            "similarity": round(segment_similarity, 4),
        })
    return sorted(hits, key=lambda item: (item["score"], item["confidence"]), reverse=True)[:10]


def _case_segments(event: PublicOpinionEvent, version: PublicOpinionEventVersion) -> list[str]:
    meta = event.source_meta if isinstance(event.source_meta, dict) else {}
    raw = meta.get("raw_import_event") if isinstance(meta.get("raw_import_event"), dict) else {}
    duplicate_records = meta.get("duplicate_records") if isinstance(meta.get("duplicate_records"), list) else []
    confirmed_facts: list[str] = []
    for record in [raw, *[item for item in duplicate_records if isinstance(item, dict)]]:
        verification = record.get("verification") if isinstance(record.get("verification"), dict) else {}
        confirmed_facts.extend(str(item) for item in (verification.get("confirmed_facts") or [])[:5])
    process = version.event_process if isinstance(version.event_process, dict) else {}
    return [
        str(raw.get("ad_copy_original") or version.source_text or ""),
        str(process.get("trigger") or ""),
        str(event.title or version.title or ""),
        " ".join(str(item) for item in version.risk_topics or []),
        " ".join(confirmed_facts),
    ]


def _similar_events(deterministic_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": hit["event_id"],
            "external_id": hit.get("external_id"),
            "title": hit["event_title"],
            "similarity": hit["score"],
            "confidence": hit["confidence"],
            "severity_level": hit["severity_level"],
            "verification_status": hit.get("verification_status"),
            "matched_text": hit.get("matched_text"),
            "historical_consequence": hit["historical_consequence"],
            "sources": hit.get("sources", []),
        }
        for hit in deterministic_hits[:5]
    ]


def _validated_ai_assessment(
    material_text: str,
    model_result: dict[str, Any],
    similar_events: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_quotes = _string_list(model_result.get("evidence_quotes", []))
    normalized_material = normalize_text(material_text)
    valid_quotes = [
        quote for quote in raw_quotes
        if _is_meaningful_quote(material_text, quote) and normalize_text(quote) in normalized_material
    ]
    risk_level = str(model_result.get("risk_level") or "uncertain")
    quote_factor = (len(valid_quotes) / len(raw_quotes)) if raw_quotes else (0.5 if risk_level == "low" else 0.0)
    allowed_case_ids = {str(item["event_id"]) for item in similar_events}
    matched_case_ids = [
        case_id for case_id in _string_list(model_result.get("matched_case_ids", []))
        if case_id in allowed_case_ids
    ]
    raw_case_ids = _string_list(model_result.get("matched_case_ids", []))
    case_factor = (len(matched_case_ids) / len(raw_case_ids)) if raw_case_ids else 1.0
    self_confidence = max(0, min(int(model_result.get("confidence") or 0), 100)) / 100
    structure_factor = 1.0 if str(model_result.get("explanation") or "").strip() else 0.6
    effective_confidence = self_confidence * quote_factor * case_factor * structure_factor
    raw_safety_score = model_result.get("safety_score")
    safety_score = int(
        raw_safety_score if raw_safety_score is not None else _SAFETY_SCORES.get(risk_level, 0)
    )
    minimum, maximum = _SAFETY_RANGES.get(risk_level, (0, 100))
    safety_score = max(minimum, min(safety_score, maximum))
    return {
        "safety_score": max(0, min(safety_score, 100)),
        "risk_level": risk_level,
        "confidence": round(effective_confidence, 3),
        "self_reported_confidence": int(model_result.get("confidence") or 0),
        "risk_topics": _string_list(model_result.get("risk_topics", [])),
        "affected_groups": _string_list(model_result.get("affected_groups", [])),
        "propagation_drivers": _string_list(model_result.get("propagation_drivers", [])),
        "evidence_quotes": valid_quotes,
        "invalid_evidence_quotes": [quote for quote in raw_quotes if quote not in valid_quotes],
        "counter_signals": _string_list(model_result.get("counter_signals", [])),
        "suggestions": _string_list(model_result.get("suggestions", [])),
        "explanation": str(model_result.get("explanation") or ""),
        "matched_case_ids": matched_case_ids,
    }


def _ai_only_result(ai: dict[str, Any]) -> dict[str, Any]:
    confidence = float(ai.get("confidence") or 0)
    risk_level = str(ai.get("risk_level") or "uncertain")
    if risk_level not in _SAFETY_SCORES or confidence <= 0:
        return _manual_review_result("AI 输出缺少可验证的完整原文证据，需人工复核", ai)
    requires_manual_review = confidence < 0.35 or risk_level == "uncertain"
    return {
        "safety_score": None if requires_manual_review else int(ai.get("safety_score") or 0),
        "risk_level": risk_level,
        "confidence": round(confidence * 100),
        "assessment_source": "ai",
        "risk_topics": _string_list(ai.get("risk_topics", [])),
        "affected_groups": _string_list(ai.get("affected_groups", [])),
        "propagation_drivers": _string_list(ai.get("propagation_drivers", [])),
        "evidence_quotes": _string_list(ai.get("evidence_quotes", [])),
        "counter_signals": _string_list(ai.get("counter_signals", [])),
        "suggestions": _string_list(ai.get("suggestions", [])) or ["建议人工复核文案完整语境"],
        "explanation": str(ai.get("explanation") or ""),
        "requires_manual_review": requires_manual_review,
        "disagreement_reason": "AI 有效证据或置信度不足" if requires_manual_review else None,
    }


def _manual_review_result(reason: str, ai: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "safety_score": None,
        "risk_level": "uncertain",
        "confidence": 0,
        "assessment_source": "ai",
        "risk_topics": [],
        "affected_groups": [],
        "propagation_drivers": [],
        "evidence_quotes": [],
        "counter_signals": _string_list((ai or {}).get("counter_signals", [])),
        "suggestions": ["当前不能形成可靠自动结论，请人工复核"],
        "explanation": reason,
        "requires_manual_review": True,
        "disagreement_reason": reason,
    }


def _selected_similar_events(
    candidate_events: list[dict[str, Any]],
    matched_case_ids: list[str],
) -> list[dict[str, Any]]:
    selected = {str(case_id) for case_id in matched_case_ids}
    return [
        {
            "event_id": event["event_id"],
            "external_id": event.get("external_id"),
            "title": event.get("title"),
            "severity_level": event.get("severity_level"),
            "verification_status": event.get("verification_status"),
            "historical_consequence": event.get("historical_consequence", {}),
            "sources": event.get("sources", []),
        }
        for event in candidate_events
        if str(event.get("event_id")) in selected
    ]


def _is_meaningful_quote(material_text: str, quote: str) -> bool:
    normalized = normalize_text(quote)
    if len(normalized) < 3 or normalized not in normalize_text(material_text):
        return False
    semantic_count = sum(char.isalpha() or "\u4e00" <= char <= "\u9fff" for char in quote)
    return semantic_count >= 2


def _case_tokens(version: PublicOpinionEventVersion) -> list[str]:
    tokens = [*_string_list(version.trigger_patterns), *_string_list(version.risk_topics), *_string_list(version.affected_groups)]
    process = version.event_process if isinstance(version.event_process, dict) else {}
    trigger = process.get("trigger")
    if isinstance(trigger, str) and 1 < len(trigger.strip()) <= 30:
        tokens.append(trigger.strip())
    return _dedupe([token for token in tokens if 1 < len(token) <= 30])


def _topic_matches(trigger_categories: set[str], risk_topics: list[Any]) -> bool:
    normalized_topics = {_normalize(topic) for topic in risk_topics}
    for category in trigger_categories:
        category_key = _normalize(category).replace("偏差", "").replace("争议", "")
        if any(category_key and category_key in topic.replace("偏差", "").replace("争议", "") for topic in normalized_topics):
            return True
    return False


def _load_trigger_words() -> dict[str, list[str]]:
    if not _TRIGGER_WORDS_PATH.exists():
        return {}
    try:
        data = json.loads(_TRIGGER_WORDS_PATH.read_text(encoding="utf-8"))
        return data.get("triggers", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _trigger_word_hits(material_text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for category, words in _load_trigger_words().items():
        for word in words:
            start = material_text.find(word)
            if start >= 0:
                hits.append({"category": category, "matched_word": word, "start": start, "end": start + len(word)})
    return hits


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _normalize(value: Any) -> str:
    return normalize_text(str(value or ""))
