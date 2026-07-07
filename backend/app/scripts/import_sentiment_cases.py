"""
Import sentiment cases from team JSON into the public opinion database.

Usage:
    python -m app.scripts.import_sentiment_cases [--input PATH] [--admin-id USER_ID]

Default input: D:/LDragonl/桌面/team/sentiment_cases.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import func

from app.db.session import SessionLocal
from app.models.knowledge import (
    PublicOpinionEvent,
    PublicOpinionEventStatus,
    PublicOpinionEventVersion,
    PublicOpinionLibraryVersion,
)
from app.models.user import User


def import_sentiment_cases(input_path: str, admin_id: str) -> dict:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Sentiment cases file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    events = data.get("events", [])
    if not events:
        print("No events found in the input file.")
        return {"created": 0, "updated": 0, "skipped": 0}

    created = 0
    updated = 0
    skipped = 0

    db = SessionLocal()
    try:
        actor = db.query(User).filter(User.id == admin_id).first()
        if not actor:
            raise ValueError(f"Admin user not found: {admin_id}")

        for event_data in events:
            external_id = event_data.get("external_id")
            title = event_data.get("title", "")
            ad_copy = event_data.get("ad_copy_original", "")
            trigger = event_data.get("trigger_short", "")
            outcome = event_data.get("outcome", "")
            consequences = event_data.get("consequences", {})

            source_text = f"{ad_copy}\n{trigger}" if ad_copy else trigger
            consequence_text = outcome or consequences.get("reputation", "")

            existing = (
                db.query(PublicOpinionEvent)
                .filter(PublicOpinionEvent.external_id == external_id)
                .first()
            ) if external_id else None

            if existing:
                if existing.status == PublicOpinionEventStatus.published:
                    print(f"  SKIP {external_id}: already published")
                    skipped += 1
                    continue
                existing.title = title
                existing.source_text = source_text
                existing.consequence_text = consequence_text
                existing.source_meta = event_data
                existing.updated_at = datetime.now(timezone.utc)
                print(f"  UPDATE {external_id}: {title}")
                updated += 1
                _build_version_from_team_data(db, existing, event_data, actor)
                _publish_event(db, existing, actor)
                continue

            event = PublicOpinionEvent(
                external_id=external_id,
                title=title,
                source_text=source_text,
                consequence_text=consequence_text,
                source_meta=event_data,
                status=PublicOpinionEventStatus.draft,
                created_by_id=actor.id,
                updated_by_id=actor.id,
            )
            db.add(event)
            db.flush()
            print(f"  CREATE {external_id}: {title}")
            created += 1

            _build_version_from_team_data(db, event, event_data, actor)
            _publish_event(db, event, actor)

        if created or updated:
            _create_library_version(db, actor)
            db.commit()
            print("All changes committed.")
        else:
            db.rollback()
            print("No changes detected; library snapshot was not created.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {"created": created, "updated": updated, "skipped": skipped}


def _build_version_from_team_data(db, event, event_data, actor):
    """Build PublicOpinionEventVersion directly from team JSON structured fields."""
    consequences = event_data.get("consequences", {})
    timeline = event_data.get("timeline", [])

    version_number = _next_event_version(db, event.id)

    version = PublicOpinionEventVersion(
        event_id=event.id,
        version=version_number,
        title=event.title or event_data.get("title", ""),
        industry=event_data.get("industry", []),
        platforms=event_data.get("platforms", []),
        source_text=event.source_text,
        event_process={
            "trigger": event_data.get("trigger_short", ""),
            "timeline": timeline,
            "brand_response": event_data.get("brand_response", ""),
            "outcome": event_data.get("outcome", ""),
        },
        consequences={
            "reputation": consequences.get("reputation", ""),
            "business": consequences.get("business", ""),
            "regulatory": consequences.get("regulatory", ""),
            "duration_days": consequences.get("duration_days"),
            "severity_hint": consequences.get("severity_hint"),
        },
        risk_topics=[event_data.get("risk_dimension", "")] if event_data.get("risk_dimension") else [],
        trigger_patterns=[event_data.get("trigger_short", "")] if event_data.get("trigger_short") else [],
        affected_groups=[],
        propagation_drivers=[],
        normalized_tags={},
        severity_level=consequences.get("severity_hint"),
        summary=event.title or _summarize(event.source_text),
        confidence=85,
        model_name="team-import",
        model_version="v0.5.0-direct",
        generated_at=datetime.now(timezone.utc),
        edited_by_id=actor.id,
        edit_notes="从团队舆情案例 JSON 直接导入结构化字段，无需模型整理。",
    )
    db.add(version)
    db.flush()
    print(f"    -> version {version_number} built from team data")


def _publish_event(db, event, actor):
    """Publish event without re-structuring."""
    if event.status == PublicOpinionEventStatus.published:
        print(f"    -> already published")
        return
    if not event.title.strip() and not event.source_text.strip():
        print(f"    -> publish skipped: missing title/source_text")
        return
    event.status = PublicOpinionEventStatus.published
    event.published_by_id = actor.id
    event.published_at = datetime.now(timezone.utc)
    event.updated_by_id = actor.id
    db.flush()
    print(f"    -> published")


def _create_library_version(db, actor):
    published_ids = [
        row[0]
        for row in (
            db.query(PublicOpinionEvent.id)
            .filter(PublicOpinionEvent.status == PublicOpinionEventStatus.published)
            .order_by(PublicOpinionEvent.updated_at.asc())
            .all()
        )
    ]
    latest = db.query(func.max(PublicOpinionLibraryVersion.version)).scalar()
    library_version = PublicOpinionLibraryVersion(
        version=int(latest or 0) + 1,
        event_ids=published_ids,
        event_count=len(published_ids),
        notes="团队舆情案例导入后自动生成快照",
        created_by_id=actor.id,
    )
    db.add(library_version)
    db.flush()
    print(f"\nLibrary version {library_version.version} created with {library_version.event_count} events.")
    return library_version


def _next_event_version(db, event_id: str) -> int:
    latest = (
        db.query(func.max(PublicOpinionEventVersion.version))
        .filter(PublicOpinionEventVersion.event_id == event_id)
        .scalar()
    )
    return int(latest or 0) + 1


def _summarize(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:60] if compact else "未命名舆情事件"


def main():
    parser = argparse.ArgumentParser(description="Import sentiment cases from team JSON")
    parser.add_argument(
        "--input", "-i",
        default=r"D:\LDragonl\桌面\team\sentiment_cases.json",
        help="Path to sentiment_cases.json",
    )
    parser.add_argument(
        "--admin-id",
        default=None,
        help="Admin user ID (defaults to first admin found)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if not args.admin_id:
            admin = db.query(User).filter(User.role == "admin").first()
            if not admin:
                print("ERROR: No admin user found. Create an admin user first or pass --admin-id.")
                sys.exit(1)
            args.admin_id = admin.id
            print(f"Using admin user: {admin.display_name} ({admin.id})")
    finally:
        db.close()

    try:
        result = import_sentiment_cases(args.input, args.admin_id)
        print(f"\nImport complete: {result['created']} created, {result['updated']} updated, {result['skipped']} skipped.")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
