import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.knowledge import PublicOpinionEvent, PublicOpinionLibraryVersion
from app.models.user import User, UserRole
from app.services.public_opinion_case_service import (
    BUILTIN_CASES_PATH,
    normalize_public_opinion_payload,
    sync_case_file,
)


def _session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _admin(db):
    admin = User(
        id="case-admin",
        username="case-admin",
        password="x",
        display_name="管理员",
        role=UserRole.admin,
        dept_name="管理部",
    )
    db.add(admin)
    db.commit()
    return admin


def test_builtin_case_payload_normalizes_and_merges_taoli_duplicate():
    payload = json.loads(Path(BUILTIN_CASES_PATH).read_text(encoding="utf-8"))
    result = normalize_public_opinion_payload(payload)

    assert result["total_items"] == 34
    assert result["valid_items"] == 33
    assert result["invalid_items"] == 0
    taoli = next(item for item in result["valid_events"] if item["external_id"] == "sent-case-018")
    assert taoli["structured"]["occurred_at"] == "2025-09-01"
    assert taoli["structured"]["severity_level"] == "medium"
    assert taoli["structured"]["normalized_tags"]["source_aliases"] == ["sent-case-033"]
    assert "苦难营销" in taoli["structured"]["risk_topics"]
    assert len(taoli["structured"]["sources"]) >= 7


def test_builtin_case_sync_is_idempotent_and_creates_one_taoli_event():
    factory = _session_factory()
    db = factory()
    try:
        admin = _admin(db)
        first = sync_case_file(db, admin)
        db.commit()
        assert first["created"] == 33
        assert first["snapshot_changed"] is True
        assert db.query(PublicOpinionEvent).count() == 33
        assert db.query(PublicOpinionEvent).filter_by(external_id="sent-case-018").count() == 1
        assert db.query(PublicOpinionEvent).filter_by(external_id="sent-case-033").count() == 0
        assert db.query(PublicOpinionLibraryVersion).count() == 1

        second = sync_case_file(db, admin)
        db.commit()
        assert second["created"] == 0
        assert second["updated"] == 0
        assert second["snapshot_changed"] is False
        assert db.query(PublicOpinionLibraryVersion).count() == 1
    finally:
        db.close()
