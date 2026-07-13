"""Idempotent import of repository knowledge into the runtime knowledge tables."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.knowledge import (
    KnowledgeImportJob,
    KnowledgeImportJobStatus,
    PlatformRuleSet,
    PlatformRuleStatus,
    PlatformRuleVersion,
    PublicOpinionEvent,
    PublicOpinionEventStatus,
    PublicOpinionEventVersion,
    PublicOpinionLibraryVersion,
)
from app.models.user import User, UserRole


_REPO_ROOT = Path(__file__).resolve().parents[3]
_L4_ROOT = _REPO_ROOT / "knowledge" / "L4_platforms"
_L3_ROOT = _REPO_ROOT / "knowledge" / "L3_cases"
_NORMATIVE_MARKERS = ("不得", "禁止", "严禁", "不应", "违规", "虚假", "夸大", "欺诈", "限制")
_PLATFORM_KEYS = {
    "拼多多": "pinduoduo",
    "淘宝": "taobao",
    "京东": "jingdong",
    "小红书": "xiaohongshu",
    "微博": "weibo",
    "微信广告": "wechat",
}


def bootstrap_builtin_knowledge(db: Session) -> dict[str, Any]:
    """Fill missing baseline knowledge without changing administrator-managed active rules."""
    admin = db.query(User).filter(User.role == UserRole.admin).order_by(User.created_at.asc()).first()
    if not admin:
        return {"status": "skipped", "reason": "missing_admin", "platforms": 0, "cases": 0}

    summary: dict[str, Any] = {"status": "completed", "platforms": 0, "rules": 0, "cases": 0, "skipped": [], "failures": []}
    for directory in sorted(path for path in _L4_ROOT.iterdir() if path.is_dir()) if _L4_ROOT.exists() else []:
        try:
            imported = _bootstrap_platform(db, admin, directory)
            if imported is None:
                summary["skipped"].append(directory.name)
            else:
                summary["platforms"] += 1
                summary["rules"] += imported
        except Exception as exc:  # One bad source must not block other platforms.
            db.rollback()
            summary["failures"].append({"source": _relative(directory), "error": str(exc)[:180]})

    try:
        summary["cases"] = _bootstrap_public_opinion_cases(db, admin)
    except Exception as exc:
        db.rollback()
        summary["failures"].append({"source": _relative(_L3_ROOT), "error": str(exc)[:180]})

    if summary["platforms"] == 0 and summary["cases"] == 0 and not summary["failures"]:
        summary["status"] = "skipped"
        return summary

    job = KnowledgeImportJob(
        import_type="builtin_baseline",
        file_name="knowledge/L3_cases + knowledge/L4_platforms",
        status=KnowledgeImportJobStatus.completed if not summary["failures"] else KnowledgeImportJobStatus.failed,
        total_items=summary["platforms"] + summary["cases"],
        valid_items=summary["rules"] + summary["cases"],
        invalid_items=len(summary["failures"]),
        error_summary={"failures": summary["failures"]},
        options={"summary": {key: value for key, value in summary.items() if key != "failures"}},
        created_by_id=admin.id,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    return summary


def _bootstrap_platform(db: Session, admin: User, directory: Path) -> int | None:
    platform_name = _PLATFORM_KEYS.get(directory.name, _slug(directory.name))
    rule_set = db.query(PlatformRuleSet).filter(PlatformRuleSet.platform_name == platform_name).first()
    if rule_set is not None:
        active = (
            db.query(PlatformRuleVersion)
            .filter(PlatformRuleVersion.rule_set_id == rule_set.id, PlatformRuleVersion.status == PlatformRuleStatus.active)
            .first()
        )
        if active:
            return None
    else:
        rule_set = PlatformRuleSet(platform_name=platform_name, display_name=directory.name, description="内置平台规则基线")
        db.add(rule_set)
        db.flush()

    files = sorted(directory.rglob("*.txt")) + sorted(directory.rglob("*.md"))
    raw_parts: list[str] = []
    rules: list[dict[str, Any]] = []
    for file_path in files:
        text = _read_text(file_path)
        if not text:
            continue
        raw_parts.append(f"\n\n# {_relative(file_path)}\n{text}")
        rules.extend(_parse_platform_rules(text, file_path))

    if not rules:
        raise ValueError("未提取到可用规范性条款")
    raw_text = "".join(raw_parts)
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:12]
    version = PlatformRuleVersion(
        rule_set_id=rule_set.id,
        version_label=f"builtin-{digest}",
        source_name=f"内置资料库 / {directory.name}",
        raw_text=raw_text[:500_000],
        structured_rules=rules,
        status=PlatformRuleStatus.active,
        imported_by_id=admin.id,
        activated_by_id=admin.id,
        activated_at=datetime.now(timezone.utc),
    )
    db.add(version)
    db.commit()
    return len(rules)


def _bootstrap_public_opinion_cases(db: Session, admin: User) -> int:
    existing_library = db.query(PublicOpinionLibraryVersion).filter(PublicOpinionLibraryVersion.event_count > 0).first()
    if existing_library or not _L3_ROOT.exists():
        return 0

    created = 0
    for file_path in sorted(_L3_ROOT.rglob("*.txt"))[:80]:
        source_text = _read_text(file_path)
        if len(source_text.strip()) < 30:
            continue
        external_id = f"builtin:{_relative(file_path)}"
        if db.query(PublicOpinionEvent).filter(PublicOpinionEvent.external_id == external_id).first():
            continue
        title = file_path.stem[:190]
        tokens = _keywords(source_text)[:12]
        event = PublicOpinionEvent(
            external_id=external_id,
            title=title,
            source_text=source_text[:100_000],
            source_meta={"source_path": _relative(file_path), "source_hash": _hash(source_text)},
            status=PublicOpinionEventStatus.published,
            created_by_id=admin.id,
            updated_by_id=admin.id,
            published_by_id=admin.id,
            published_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()
        db.add(PublicOpinionEventVersion(
            event_id=event.id,
            version=1,
            title=title,
            source_text=source_text[:100_000],
            sources=[{"path": _relative(file_path)}],
            event_process={"trigger": tokens[0] if tokens else ""},
            consequences={"summary": source_text[:300]},
            risk_topics=tokens[:6],
            trigger_patterns=tokens,
            affected_groups=[],
            propagation_drivers=[],
            normalized_tags={"source": "builtin"},
            severity_level="medium",
            summary=source_text[:500],
            confidence=50,
            model_name="builtin-parser",
            generated_at=datetime.now(timezone.utc),
        ))
        created += 1

    db.flush()
    events = db.query(PublicOpinionEvent).filter(PublicOpinionEvent.status == PublicOpinionEventStatus.published).all()
    if events:
        next_version = (db.query(func.max(PublicOpinionLibraryVersion.version)).scalar() or 0) + 1
        db.add(PublicOpinionLibraryVersion(
            version=next_version,
            event_ids=[event.id for event in events],
            event_count=len(events),
            notes="内置舆情案例基线",
            created_by_id=admin.id,
        ))
    db.commit()
    return created


def _parse_platform_rules(text: str, file_path: Path) -> list[dict[str, Any]]:
    statements = re.split(r"(?:[。！？；\n]+)", text)
    result: list[dict[str, Any]] = []
    source = _relative(file_path)
    for statement in statements:
        normalized = " ".join(statement.split())
        if not (12 <= len(normalized) <= 420) or not any(marker in normalized for marker in _NORMATIVE_MARKERS):
            continue
        digest = hashlib.sha1(f"{source}:{normalized}".encode("utf-8")).hexdigest()[:10]
        result.append({
            "rule_id": f"builtin-{digest}",
            "title": file_path.stem[:100],
            "text": normalized,
            "keywords": _keywords(normalized)[:12],
            "risk_level": "平台规则",
            "source_path": source,
            "source_hash": _hash(normalized),
        })
    return result


def _keywords(text: str) -> list[str]:
    phrases = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    seen: set[str] = set()
    result: list[str] = []
    for phrase in phrases:
        if phrase in seen or phrase in _NORMATIVE_MARKERS:
            continue
        seen.add(phrase)
        result.append(phrase)
    return result


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            return ""
    return ""


def _relative(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or value
