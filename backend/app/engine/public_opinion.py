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
_RISK_SCORES = {"low": 15, "medium": 45, "high": 70, "severe": 90, "uncertain": 0}
_GENERIC_BIGRAMS = {"这个", "一种", "可以", "可能", "我们", "你们", "他们", "没有", "不是", "广告", "文案"}


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
    similar_events = _similar_events(deterministic_hits)
    local = _local_assessment(deterministic_hits, similar_events, trigger_word_hits)

    model_error: str | None = None
    try:
        model_result = model_service.explain_public_opinion_risk(
            db=db,
            material_text=material_text,
            deterministic_hits=deterministic_hits,
            similar_events=similar_events,
            trigger_word_hits=trigger_word_hits,
        )
        ai = _validated_ai_assessment(material_text, model_result, similar_events)
        result = _fuse_assessments(local, ai)
        model_available = True
    except model_service.ModelServiceError as exc:
        model_error = str(exc)[:200]
        result = _local_only_result(local)
        model_available = False

    result.update({
        "status": "succeeded" if model_available else ("model_unavailable" if local["confidence"] > 0 else "uncertain"),
        "model_available": model_available,
        "model_error": model_error,
        "similar_events": similar_events,
        "deterministic_hits": deterministic_hits,
        "trigger_word_hits": trigger_word_hits,
        "library_version_id": library_version.id if library_version else None,
        "library_version": library_version.version if library_version else None,
        "knowledge_base_available": bool(cases),
    })
    return PublicOpinionReview(
        status="succeeded",
        library_version_id=library_version.id if library_version else None,
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


def _local_assessment(
    deterministic_hits: list[dict[str, Any]],
    similar_events: list[dict[str, Any]],
    trigger_word_hits: list[dict[str, Any]],
) -> dict[str, Any]:
    trigger_topics = [str(hit["category"]) for hit in trigger_word_hits]
    if not deterministic_hits:
        if not trigger_word_hits:
            return {
                "risk_score": 0,
                "risk_level": "uncertain",
                "confidence": 0.0,
                "risk_topics": [],
                "evidence_quotes": [],
                "suggestions": ["当前没有足够的本地舆情证据，需结合 AI 或人工复核"],
                "explanation": "未命中可信相似案例或明确上下文证据。",
                "similar_events": [],
            }
        return {
            "risk_score": min(10 + len(trigger_word_hits) * 2, 20),
            "risk_level": "low",
            "confidence": min(0.25, 0.12 + len(trigger_word_hits) * 0.03),
            "risk_topics": _dedupe(trigger_topics),
            "evidence_quotes": [str(hit["matched_word"]) for hit in trigger_word_hits],
            "suggestions": ["触发词仅构成弱线索，请结合完整语境复核"],
            "explanation": "仅命中候选触发词，不能据此直接判定中高风险。",
            "similar_events": [],
        }

    top = deterministic_hits[0]
    score = int(top["score"])
    severity = str(top.get("severity_level") or "").lower()
    if severity == "high" and score >= 50:
        score = max(65, min(score, 79))
    elif severity == "medium" and score >= 25:
        score = max(30, min(score, 59))
    elif severity == "severe" and score >= 55:
        score = max(score, 80)
    elif severity == "low":
        score = min(score, 29)
    topics = _dedupe([
        *_flatten(hit.get("risk_topics", []) for hit in deterministic_hits[:3]),
        *trigger_topics,
    ])
    return {
        "risk_score": min(score, 100),
        "risk_level": _score_to_level(score),
        "confidence": float(top["confidence"]),
        "risk_topics": topics,
        "evidence_quotes": [str(top.get("matched_text") or "")],
        "suggestions": ["建议参考相似真实案例复核表达方式、价值观和传播风险"],
        "explanation": f"本地检索命中相似事件“{top['event_title']}”，匹配依据：{top.get('matched_text') or '文本相似'}。",
        "similar_events": similar_events,
    }


def _validated_ai_assessment(
    material_text: str,
    model_result: dict[str, Any],
    similar_events: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_quotes = _string_list(model_result.get("evidence_quotes", []))
    normalized_material = normalize_text(material_text)
    valid_quotes = [quote for quote in raw_quotes if normalize_text(quote) in normalized_material]
    quote_factor = (len(valid_quotes) / len(raw_quotes)) if raw_quotes else 0.35
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
    risk_level = str(model_result.get("risk_level") or "uncertain")
    risk_score = int(model_result.get("risk_score") or _RISK_SCORES.get(risk_level, 0))
    return {
        "risk_score": max(0, min(risk_score, 100)),
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


def _fuse_assessments(local: dict[str, Any], ai: dict[str, Any]) -> dict[str, Any]:
    local_confidence = float(local.get("confidence") or 0)
    ai_confidence = float(ai.get("confidence") or 0)
    local_weight = 0.60 * local_confidence
    ai_weight = 0.40 * ai_confidence
    if local_weight <= 0 and ai_weight <= 0:
        return _uncertain_result(local, ai)
    if local_weight <= 0:
        final_score = int(ai["risk_score"])
        source = "ai"
    elif ai_weight <= 0:
        final_score = int(local["risk_score"])
        source = "local"
    else:
        final_score = round(
            ((int(local["risk_score"]) * local_weight) + (int(ai["risk_score"]) * ai_weight))
            / (local_weight + ai_weight)
        )
        source = "hybrid"

    if local_confidence >= 0.70 and local["risk_score"] >= 30:
        final_score = max(final_score, int(local["risk_score"]))
    disagreement = (
        local_confidence >= 0.65
        and ai_confidence >= 0.65
        and abs(int(local["risk_score"]) - int(ai["risk_score"])) >= 30
    )
    if disagreement:
        final_score = max(int(local["risk_score"]), int(ai["risk_score"]))
    final_confidence = (
        ((local_confidence * local_weight) + (ai_confidence * ai_weight)) / (local_weight + ai_weight)
        if local_weight + ai_weight > 0 else 0
    )
    suggestions = _dedupe([*_string_list(local.get("suggestions", [])), *_string_list(ai.get("suggestions", []))])
    return {
        "risk_score": final_score,
        "risk_level": _score_to_level(final_score),
        "confidence": round(final_confidence * 100),
        "assessment_source": source,
        "risk_topics": _dedupe([*_string_list(local.get("risk_topics", [])), *_string_list(ai.get("risk_topics", []))]),
        "affected_groups": ai.get("affected_groups", []),
        "propagation_drivers": ai.get("propagation_drivers", []),
        "evidence_quotes": _dedupe([*_string_list(local.get("evidence_quotes", [])), *_string_list(ai.get("evidence_quotes", []))]),
        "counter_signals": ai.get("counter_signals", []),
        "suggestions": suggestions or ["建议人工复核文案语境"],
        "explanation": " ".join(value for value in (local.get("explanation"), ai.get("explanation")) if value),
        "requires_manual_review": disagreement,
        "disagreement_reason": "本地案例证据与 AI 语义判断存在高可信分歧" if disagreement else None,
        "local_assessment": local,
        "ai_assessment": ai,
    }


def _local_only_result(local: dict[str, Any]) -> dict[str, Any]:
    if float(local.get("confidence") or 0) <= 0:
        return _uncertain_result(local, None)
    return {
        **local,
        "confidence": round(float(local["confidence"]) * 100),
        "assessment_source": "local",
        "requires_manual_review": False,
        "disagreement_reason": None,
        "local_assessment": local,
        "ai_assessment": None,
    }


def _uncertain_result(local: dict[str, Any], ai: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "risk_score": 0,
        "risk_level": "uncertain",
        "confidence": 0,
        "assessment_source": "ai" if ai and ai.get("confidence") else "local",
        "risk_topics": _dedupe([*_string_list(local.get("risk_topics", [])), *_string_list((ai or {}).get("risk_topics", []))]),
        "affected_groups": [],
        "propagation_drivers": [],
        "evidence_quotes": [],
        "counter_signals": _string_list((ai or {}).get("counter_signals", [])),
        "suggestions": ["当前没有足够可信证据，请人工复核"],
        "explanation": "本地与 AI 均未提供足够可信证据，不能直接判断为低风险。",
        "requires_manual_review": True,
        "disagreement_reason": "有效证据不足",
        "local_assessment": local,
        "ai_assessment": ai,
    }


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


def _score_to_level(score: int) -> str:
    if score >= 80:
        return "severe"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _flatten(groups) -> list[str]:
    result: list[str] = []
    for group in groups:
        result.extend(_string_list(group))
    return result


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
