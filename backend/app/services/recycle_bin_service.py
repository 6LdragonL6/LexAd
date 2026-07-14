from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.admin import RecycleBinEntry
from app.models.brand import Brand
from app.models.knowledge import (
    KnowledgeAuditLog,
    PlatformRuleSet,
    PlatformRuleVersion,
    PublicOpinionEvent,
    PublicOpinionEventVersion,
    PublicOpinionLibraryVersion,
)
from app.models.material import Material, MaterialStatus, MaterialSubmissionSnapshot
from app.models.review import Review
from app.models.user import User


RETENTION_DAYS = 15
TARGET_MODELS = {
    "material": Material,
    "brand": Brand,
    "public_opinion_event": PublicOpinionEvent,
    "platform_rule_set": PlatformRuleSet,
}


class RecycleBinError(ValueError):
    pass


def list_entries(
    db: Session,
    *,
    target_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    query = db.query(RecycleBinEntry)
    if target_type:
        if target_type not in TARGET_MODELS:
            raise RecycleBinError("不支持的回收站类型")
        query = query.filter(RecycleBinEntry.target_type == target_type)
    total = query.count()
    entries = (
        query.order_by(RecycleBinEntry.deleted_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    now = datetime.now(timezone.utc)
    items = []
    for entry in entries:
        purge_after = _as_utc(entry.purge_after)
        remaining_seconds = max(0, (purge_after - now).total_seconds())
        items.append(
            {
                "id": entry.id,
                "target_type": entry.target_type,
                "target_id": entry.target_id,
                "display_name": entry.display_name,
                "deleted_by_id": entry.deleted_by_id,
                "deleted_at": entry.deleted_at,
                "purge_after": entry.purge_after,
                "remaining_days": math.ceil(remaining_seconds / 86400),
            }
        )
    return items, total


def move_to_recycle_bin(db: Session, target_type: str, target_id: str, actor: User) -> RecycleBinEntry:
    model = TARGET_MODELS.get(target_type)
    if model is None:
        raise RecycleBinError("不支持的删除类型")
    target = db.query(model).filter(model.id == target_id, model.deleted_at.is_(None)).first()
    if target is None:
        raise RecycleBinError("对象不存在或已在回收站中")

    now = datetime.now(timezone.utc)
    previous_state = _previous_state(target_type, target)
    if target_type == "material":
        _interrupt_material_reviews(db, target.id, now)

    target.deleted_at = now
    target.deleted_by_id = actor.id
    target.purge_after = now + timedelta(days=RETENTION_DAYS)
    entry = RecycleBinEntry(
        target_type=target_type,
        target_id=target_id,
        display_name=_display_name(target_type, target),
        deleted_by_id=actor.id,
        deleted_at=now,
        purge_after=target.purge_after,
        previous_state=previous_state,
    )
    db.add(entry)
    _audit(db, actor.id, "recycle_bin.delete", target_type, target_id, "对象已移入回收站")
    db.commit()
    db.refresh(entry)
    return entry


def restore_entry(db: Session, entry_id: str, actor: User) -> None:
    entry = db.query(RecycleBinEntry).filter(RecycleBinEntry.id == entry_id).first()
    if entry is None:
        raise RecycleBinError("回收站记录不存在")
    model = TARGET_MODELS.get(entry.target_type)
    target = db.query(model).filter(model.id == entry.target_id).first() if model else None
    if target is None:
        raise RecycleBinError("原对象已不存在，无法恢复")

    if entry.target_type == "material":
        previous_status = entry.previous_state.get("status")
        target.status = MaterialStatus.draft if previous_status == "ai_reviewing" else MaterialStatus(previous_status)

    target.deleted_at = None
    target.deleted_by_id = None
    target.purge_after = None
    _audit(db, actor.id, "recycle_bin.restore", entry.target_type, entry.target_id, "对象已恢复")
    db.delete(entry)
    db.commit()


def purge_entry(db: Session, entry_id: str, actor: User) -> None:
    entry = db.query(RecycleBinEntry).filter(RecycleBinEntry.id == entry_id).first()
    if entry is None:
        raise RecycleBinError("回收站记录不存在")
    _purge(db, entry, actor.id, automatic=False)
    db.commit()


def cleanup_expired_entries() -> int:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        entry_ids = [
            row[0]
            for row in db.query(RecycleBinEntry.id)
            .filter(RecycleBinEntry.purge_after <= now)
            .order_by(RecycleBinEntry.purge_after.asc())
            .all()
        ]
        cleaned = 0
        for entry_id in entry_ids:
            try:
                entry = db.query(RecycleBinEntry).filter(RecycleBinEntry.id == entry_id).first()
                if entry is None:
                    continue
                _purge(db, entry, entry.deleted_by_id, automatic=True)
                db.commit()
                cleaned += 1
            except Exception:
                db.rollback()
        return cleaned
    finally:
        db.close()


def _purge(db: Session, entry: RecycleBinEntry, actor_id: str, *, automatic: bool) -> None:
    model = TARGET_MODELS.get(entry.target_type)
    target = db.query(model).filter(model.id == entry.target_id).first() if model else None
    if target is not None:
        if entry.target_type == "material":
            db.query(Review).filter(Review.material_id == target.id).delete(synchronize_session=False)
            db.query(MaterialSubmissionSnapshot).filter(
                MaterialSubmissionSnapshot.material_id == target.id
            ).delete(synchronize_session=False)
        elif entry.target_type == "brand":
            db.query(Material).filter(Material.brand_id == target.id).update(
                {Material.brand_id: None}, synchronize_session=False
            )
        elif entry.target_type == "public_opinion_event":
            db.query(PublicOpinionEventVersion).filter(
                PublicOpinionEventVersion.event_id == target.id
            ).delete(synchronize_session=False)
            for library in db.query(PublicOpinionLibraryVersion).all():
                event_ids = [event_id for event_id in (library.event_ids or []) if event_id != target.id]
                if event_ids != (library.event_ids or []):
                    library.event_ids = event_ids
                    library.event_count = len(event_ids)
        elif entry.target_type == "platform_rule_set":
            db.query(PlatformRuleVersion).filter(
                PlatformRuleVersion.rule_set_id == target.id
            ).delete(synchronize_session=False)
        db.delete(target)

    action = "recycle_bin.auto_purge" if automatic else "recycle_bin.purge"
    message = "到期自动永久清理" if automatic else "管理员永久清理"
    _audit(db, actor_id, action, entry.target_type, entry.target_id, message)
    db.delete(entry)


def _interrupt_material_reviews(db: Session, material_id: str, now: datetime) -> None:
    reviews = db.query(Review).filter(Review.material_id == material_id, Review.task_status == "processing").all()
    for review in reviews:
        review.task_status = "failed"
        review.error_message = "物料已由管理员移入回收站"
        review.completed_at = now


def _previous_state(target_type: str, target) -> dict:
    state = {}
    if target_type in {"material", "brand", "public_opinion_event"}:
        status = target.status.value if hasattr(target.status, "value") else target.status
        state["status"] = status
    return state


def _display_name(target_type: str, target) -> str:
    if target_type == "platform_rule_set":
        return target.display_name or target.platform_name
    return getattr(target, "name", None) or getattr(target, "title", None) or target.id


def _audit(db: Session, actor_id: str, action: str, target_type: str, target_id: str, message: str) -> None:
    db.add(
        KnowledgeAuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_state={},
            after_state={},
            message=message,
        )
    )


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
