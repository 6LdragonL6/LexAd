from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.knowledge import (
    PublicOpinionEvent,
    PublicOpinionEventStatus,
    PublicOpinionEventVersion,
    PublicOpinionLibraryVersion,
)
from app.models.user import User


REPO_ROOT = Path(__file__).resolve().parents[3]
BUILTIN_CASES_PATH = REPO_ROOT / "data" / "sentiment_cases.json"
BUILTIN_IMPORT_SOURCE = "builtin_sentiment_cases"
_TAOLI_CANONICAL_ID = "sent-case-018"
_TAOLI_ALIAS_ID = "sent-case-033"


def normalize_public_opinion_payload(payload: dict[str, Any]) -> dict[str, Any]:
    schema_errors: list[str] = []
    item_errors: list[dict[str, Any]] = []
    if payload.get("schema_version") != "1.0":
        schema_errors.append("schema_version 必须为 1.0")
    events = payload.get("events")
    if not isinstance(events, list):
        schema_errors.append("events 必须是事件数组")
        events = []

    normalized: list[dict[str, Any]] = []
    seen_external_ids: set[str] = set()
    for index, event in enumerate(events):
        errors = _validate_source_event(event)
        external_id = event.get("external_id") if isinstance(event, dict) else None
        if external_id and external_id in seen_external_ids:
            errors.append("同一文件中 external_id 重复")
        if external_id:
            seen_external_ids.add(external_id)
        if errors:
            item_errors.append({"index": index, "external_id": external_id, "errors": errors})
            continue
        normalized.append(_normalize_source_event(event))

    canonical, duplicate_errors = _canonicalize_duplicates(normalized)
    item_errors.extend(duplicate_errors)
    return {
        "total_items": len(events),
        "valid_items": len(canonical),
        "invalid_items": len(item_errors) + len(schema_errors),
        "schema_errors": schema_errors,
        "item_errors": item_errors,
        "valid_events": canonical,
    }


def sync_case_file(
    db: Session,
    actor: User,
    path: Path = BUILTIN_CASES_PATH,
    *,
    import_source: str = BUILTIN_IMPORT_SOURCE,
) -> dict[str, int | bool]:
    if not path.exists():
        return {"created": 0, "updated": 0, "skipped": 0, "canonical_count": 0, "snapshot_changed": False}
    payload = json.loads(path.read_text(encoding="utf-8"))
    normalized = normalize_public_opinion_payload(payload)
    if normalized["schema_errors"] or normalized["item_errors"]:
        details = normalized["schema_errors"] or normalized["item_errors"][:3]
        raise ValueError(f"内置舆情案例校验失败：{details}")

    created = 0
    updated = 0
    skipped = 0
    changed = False
    for item in normalized["valid_events"]:
        external_id = item.get("external_id")
        existing = (
            db.query(PublicOpinionEvent).filter(PublicOpinionEvent.external_id == external_id).first()
            if external_id
            else None
        )
        source_hash = item["source_meta"]["source_hash"]
        if existing:
            meta = existing.source_meta if isinstance(existing.source_meta, dict) else {}
            legacy_team_import = (
                meta.get("external_id") == external_id
                and ("ad_copy_original" in meta or "trigger_short" in meta)
            )
            if meta.get("import_source") != import_source and not legacy_team_import:
                skipped += 1
                continue
            if meta.get("source_hash") == source_hash:
                skipped += 1
                continue
            existing.title = item["title"]
            existing.source_text = item["source_text"]
            existing.consequence_text = item["consequence_text"]
            existing.source_meta = {**item["source_meta"], "import_source": import_source}
            existing.updated_by_id = actor.id
            create_structured_version(db, existing, item, actor, model_name=import_source)
            updated += 1
            changed = True
            continue

        event = PublicOpinionEvent(
            external_id=external_id,
            title=item["title"],
            source_text=item["source_text"],
            consequence_text=item["consequence_text"],
            source_meta={**item["source_meta"], "import_source": import_source},
            status=PublicOpinionEventStatus.published,
            created_by_id=actor.id,
            updated_by_id=actor.id,
            published_by_id=actor.id,
            published_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()
        create_structured_version(db, event, item, actor, model_name=import_source)
        created += 1
        changed = True

    published_ids = active_public_opinion_event_ids(db)
    latest = (
        db.query(PublicOpinionLibraryVersion)
        .order_by(PublicOpinionLibraryVersion.version.desc())
        .first()
    )
    snapshot_changed = changed or latest is None or list(latest.event_ids or []) != published_ids
    if snapshot_changed:
        next_version = int(db.query(func.max(PublicOpinionLibraryVersion.version)).scalar() or 0) + 1
        db.add(PublicOpinionLibraryVersion(
            version=next_version,
            event_ids=published_ids,
            event_count=len(published_ids),
            notes="v0.6.3 真实舆情案例基线同步",
            created_by_id=actor.id,
        ))
    db.flush()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "canonical_count": len(normalized["valid_events"]),
        "snapshot_changed": snapshot_changed,
    }


def create_structured_version(
    db: Session,
    event: PublicOpinionEvent,
    item: dict[str, Any],
    actor: User,
    *,
    model_name: str = "normalized-import",
) -> PublicOpinionEventVersion:
    structured = item.get("structured") or {}
    version = PublicOpinionEventVersion(
        event_id=event.id,
        version=_next_event_version(db, event.id),
        title=event.title,
        industry=structured.get("industry", []),
        platforms=structured.get("platforms", []),
        occurred_at=_parse_date(structured.get("occurred_at")),
        source_text=event.source_text,
        sources=structured.get("sources", []),
        event_process=structured.get("event_process", {}),
        consequences=structured.get("consequences", {}),
        risk_topics=structured.get("risk_topics", []),
        trigger_patterns=structured.get("trigger_patterns", []),
        affected_groups=structured.get("affected_groups", []),
        propagation_drivers=structured.get("propagation_drivers", []),
        normalized_tags=structured.get("normalized_tags", {}),
        severity_level=structured.get("severity_level"),
        summary=structured.get("summary", event.title),
        confidence=structured.get("confidence", 0),
        model_name=model_name,
        model_version="v0.6.3-normalized",
        generated_at=datetime.now(timezone.utc),
        edited_by_id=actor.id,
        edit_notes="由统一舆情案例规范化服务生成。",
    )
    db.add(version)
    db.flush()
    return version


def _validate_source_event(event: Any) -> list[str]:
    if not isinstance(event, dict):
        return ["事件必须是对象"]
    errors: list[str] = []
    if not str(event.get("title") or "").strip():
        errors.append("缺少标题 title")
    is_team = "ad_copy_original" in event or "trigger_short" in event
    if is_team:
        if not str(event.get("ad_copy_original") or event.get("trigger_short") or "").strip():
            errors.append("缺少原始文案 ad_copy_original 或触发摘要 trigger_short")
        if not isinstance(event.get("sources"), list) or not event.get("sources"):
            errors.append("缺少来源 sources")
    else:
        if not str(event.get("source_text") or "").strip():
            errors.append("缺少事件材料 source_text")
        process = event.get("event_process")
        if not isinstance(process, dict):
            errors.append("缺少事件过程 event_process")
        else:
            if not str(process.get("trigger") or "").strip():
                errors.append("缺少触发原因 event_process.trigger")
            if not str(process.get("outcome") or "").strip():
                errors.append("缺少事件结果 event_process.outcome")
    return errors


def _normalize_source_event(event: dict[str, Any]) -> dict[str, Any]:
    if "ad_copy_original" in event or "trigger_short" in event:
        return _normalize_team_event(event)
    return _normalize_admin_event(event)


def _normalize_team_event(event: dict[str, Any]) -> dict[str, Any]:
    raw = copy.deepcopy(event)
    ad_copy = str(event.get("ad_copy_original") or "").strip()
    trigger = str(event.get("trigger_short") or "").strip()
    source_text = "\n".join(value for value in (ad_copy, trigger) if value)
    consequences = copy.deepcopy(event.get("consequences") or {})
    verification = copy.deepcopy(event.get("verification") or {})
    verdict = str(verification.get("verdict") or "").lower()
    confidence = 90 if verdict == "confirmed" else 80 if verdict == "corrected" else 60
    risk_dimension = str(event.get("risk_dimension") or "").strip()
    event_process = {
        "trigger": trigger,
        "timeline": copy.deepcopy(event.get("timeline") or []),
        "brand_response": event.get("brand_response") or "",
        "outcome": event.get("outcome") or "",
    }
    structured = {
        "industry": copy.deepcopy(event.get("industry") or []),
        "platforms": copy.deepcopy(event.get("platforms") or []),
        "occurred_at": event.get("occurred_at"),
        "sources": copy.deepcopy(event.get("sources") or []),
        "event_process": event_process,
        "consequences": consequences,
        "risk_topics": [risk_dimension] if risk_dimension else [],
        "trigger_patterns": [trigger] if trigger else [],
        "affected_groups": [],
        "propagation_drivers": [],
        "normalized_tags": {
            "brand": event.get("brand") or "",
            "verification_verdict": verdict,
            "source_aliases": [],
        },
        "severity_level": consequences.get("severity_hint"),
        "summary": event.get("title") or "",
        "confidence": confidence,
    }
    consequence_text = str(event.get("outcome") or consequences.get("reputation") or "")
    return {
        "external_id": event.get("external_id"),
        "title": event.get("title") or "",
        "source_text": source_text,
        "consequence_text": consequence_text,
        "source_meta": {
            "brand": event.get("brand") or "",
            "verification": verification,
            "credibility_notes": event.get("credibility_notes") or "",
            "raw_import_event": raw,
            "source_hash": _source_hash(raw),
        },
        "structured": structured,
    }


def _normalize_admin_event(event: dict[str, Any]) -> dict[str, Any]:
    process = copy.deepcopy(event.get("event_process") or {})
    consequences = copy.deepcopy(event.get("consequences") or {})
    source_text = str(event.get("source_text") or "")
    consequence_text = str(
        process.get("outcome")
        or consequences.get("reputation")
        or consequences.get("business")
        or consequences.get("regulatory")
        or ""
    )
    raw = copy.deepcopy(event)
    return {
        "external_id": event.get("external_id"),
        "title": event.get("title") or "",
        "source_text": source_text,
        "consequence_text": consequence_text,
        "source_meta": {
            "notes": event.get("notes") or "",
            "raw_import_event": raw,
            "source_hash": _source_hash(raw),
        },
        "structured": {
            "industry": copy.deepcopy(event.get("industry") or []),
            "platforms": copy.deepcopy(event.get("platforms") or []),
            "occurred_at": event.get("occurred_at"),
            "sources": copy.deepcopy(event.get("sources") or []),
            "event_process": process,
            "consequences": consequences,
            "risk_topics": copy.deepcopy(event.get("risk_topics") or []),
            "trigger_patterns": [process.get("trigger")] if process.get("trigger") else [],
            "affected_groups": copy.deepcopy(event.get("affected_groups") or []),
            "propagation_drivers": copy.deepcopy(event.get("propagation_drivers") or []),
            "normalized_tags": copy.deepcopy(event.get("normalized_tags") or {}),
            "severity_level": consequences.get("severity_hint"),
            "summary": event.get("title") or "",
            "confidence": 70,
        },
    }


def _canonicalize_duplicates(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    for item in items:
        raw = item.get("source_meta", {}).get("raw_import_event", {})
        brand = _normalize_key(raw.get("brand") or item.get("title"))
        ad_copy = _normalize_key(raw.get("ad_copy_original") or item.get("source_text"))
        key = f"{brand}|{ad_copy}" if ad_copy else str(item.get("external_id") or "")
        existing = by_key.get(key)
        if not existing:
            by_key[key] = item
            result.append(item)
            continue
        ids = {str(existing.get("external_id") or ""), str(item.get("external_id") or "")}
        if ids == {_TAOLI_CANONICAL_ID, _TAOLI_ALIAS_ID}:
            canonical = existing if existing.get("external_id") == _TAOLI_CANONICAL_ID else item
            alias = item if canonical is existing else existing
            _merge_taoli_duplicate(canonical, alias)
            if canonical is not existing:
                result[result.index(existing)] = canonical
                by_key[key] = canonical
            continue
        errors.append({
            "index": -1,
            "external_id": item.get("external_id"),
            "errors": [f"与 {existing.get('external_id')} 构成语义重复，需人工确认"],
        })
    return result, errors


def _merge_taoli_duplicate(canonical: dict[str, Any], alias: dict[str, Any]) -> None:
    canonical["structured"]["occurred_at"] = "2025-09-01"
    canonical["structured"]["severity_level"] = "medium"
    canonical["structured"]["consequences"]["severity_hint"] = "medium"
    canonical["structured"]["risk_topics"] = ["价值观争议", "苦难营销"]
    canonical["structured"]["normalized_tags"]["source_aliases"] = [_TAOLI_ALIAS_ID]
    canonical["structured"]["sources"] = _merge_sources(
        canonical["structured"].get("sources", []),
        alias["structured"].get("sources", []),
    )
    canonical["source_meta"]["duplicate_records"] = [alias["source_meta"].get("raw_import_event", {})]
    canonical["source_meta"]["source_hash"] = _source_hash({
        "canonical": canonical["source_meta"].get("raw_import_event", {}),
        "aliases": canonical["source_meta"]["duplicate_records"],
    })


def _merge_sources(first: list[Any], second: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for source in [*first, *second]:
        key = str(source.get("url") or source.get("name") or "") if isinstance(source, dict) else str(source)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(source)
    return result


def active_public_opinion_event_ids(db: Session) -> list[str]:
    events = (
        db.query(PublicOpinionEvent)
        .filter(
            PublicOpinionEvent.status == PublicOpinionEventStatus.published,
            PublicOpinionEvent.deleted_at.is_(None),
        )
        .order_by(PublicOpinionEvent.updated_at.asc(), PublicOpinionEvent.id.asc())
        .all()
    )
    return [
        event.id
        for event in events
        if not _is_legacy_l3_baseline(event) and event.external_id != _TAOLI_ALIAS_ID
    ]


def _is_legacy_l3_baseline(event: PublicOpinionEvent) -> bool:
    if not str(event.external_id or "").startswith("builtin:knowledge/L3_cases/"):
        return False
    meta = event.source_meta if isinstance(event.source_meta, dict) else {}
    return str(meta.get("source_path") or "").startswith("knowledge/L3_cases/")


def _next_event_version(db: Session, event_id: str) -> int:
    latest = (
        db.query(func.max(PublicOpinionEventVersion.version))
        .filter(PublicOpinionEventVersion.event_id == event_id)
        .scalar()
    )
    return int(latest or 0) + 1


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(value or "").lower())


def _source_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
