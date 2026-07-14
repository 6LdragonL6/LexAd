from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.admin import RecycleBinEntry
from app.models.brand import Brand
from app.models.knowledge import PlatformRuleSet, PlatformRuleVersion, PublicOpinionEvent, PublicOpinionEventVersion
from app.models.material import Material, MaterialStatus, MaterialSubmissionSnapshot
from app.models.review import Review
from app.models.user import User, UserRole
from app.services import material_service, recycle_bin_service


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _seed(db):
    admin = User(
        id="admin-recycle-1",
        username="admin-recycle",
        password="not-used",
        display_name="管理员",
        role=UserRole.admin,
        dept_name="管理部",
    )
    brand = Brand(id="brand-recycle-1", name="测试品牌", created_by_id=admin.id)
    material = Material(
        id="material-recycle-1",
        name="测试物料",
        raw_text="测试文案",
        submitter_id=admin.id,
        brand_id=brand.id,
        status=MaterialStatus.ai_reviewing,
    )
    snapshot = MaterialSubmissionSnapshot(
        id="snapshot-recycle-1",
        material_id=material.id,
        version=1,
        name=material.name,
    )
    review = Review(
        id="review-recycle-1",
        material_id=material.id,
        submission_snapshot_id=snapshot.id,
        task_status="processing",
    )
    event = PublicOpinionEvent(
        id="event-recycle-1",
        title="测试舆情",
        source_text="事件",
        created_by_id=admin.id,
    )
    event_version = PublicOpinionEventVersion(
        id="event-version-recycle-1",
        event_id=event.id,
        version=1,
    )
    rule_set = PlatformRuleSet(
        id="rules-recycle-1",
        platform_name="recycle-platform",
        display_name="测试平台",
    )
    rule_version = PlatformRuleVersion(
        id="rule-version-recycle-1",
        rule_set_id=rule_set.id,
        version_label="v1",
        imported_by_id=admin.id,
    )
    db.add_all([admin, brand, material, snapshot, review, event, event_version, rule_set, rule_version])
    db.commit()
    return admin


def test_material_delete_restore_and_purge_preserves_relationships_until_purge():
    factory = _session_factory()
    db = factory()
    admin = _seed(db)

    entry = recycle_bin_service.move_to_recycle_bin(db, "material", "material-recycle-1", admin)
    assert material_service.get_material(db, "material-recycle-1") is None
    assert db.get(Review, "review-recycle-1").task_status == "failed"
    assert entry.purge_after > entry.deleted_at

    recycle_bin_service.restore_entry(db, entry.id, admin)
    restored = material_service.get_material(db, "material-recycle-1")
    assert restored is not None
    assert restored.status == MaterialStatus.draft

    entry = recycle_bin_service.move_to_recycle_bin(db, "material", restored.id, admin)
    recycle_bin_service.purge_entry(db, entry.id, admin)
    assert db.get(Material, restored.id) is None
    assert db.get(Review, "review-recycle-1") is None
    assert db.get(MaterialSubmissionSnapshot, "snapshot-recycle-1") is None
    db.close()


def test_brand_event_and_rule_set_purge_cleanup_children_without_deleting_material():
    factory = _session_factory()
    db = factory()
    admin = _seed(db)

    brand_entry = recycle_bin_service.move_to_recycle_bin(db, "brand", "brand-recycle-1", admin)
    recycle_bin_service.purge_entry(db, brand_entry.id, admin)
    assert db.get(Brand, "brand-recycle-1") is None
    assert db.get(Material, "material-recycle-1").brand_id is None

    event_entry = recycle_bin_service.move_to_recycle_bin(db, "public_opinion_event", "event-recycle-1", admin)
    recycle_bin_service.purge_entry(db, event_entry.id, admin)
    assert db.get(PublicOpinionEvent, "event-recycle-1") is None
    assert db.get(PublicOpinionEventVersion, "event-version-recycle-1") is None

    rules_entry = recycle_bin_service.move_to_recycle_bin(db, "platform_rule_set", "rules-recycle-1", admin)
    recycle_bin_service.purge_entry(db, rules_entry.id, admin)
    assert db.get(PlatformRuleSet, "rules-recycle-1") is None
    assert db.get(PlatformRuleVersion, "rule-version-recycle-1") is None
    assert db.query(RecycleBinEntry).count() == 0
    db.close()


def test_expired_entries_are_cleaned_idempotently(monkeypatch):
    factory = _session_factory()
    db = factory()
    admin = _seed(db)
    entry = recycle_bin_service.move_to_recycle_bin(db, "brand", "brand-recycle-1", admin)
    entry.purge_after = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    db.close()

    monkeypatch.setattr(recycle_bin_service, "SessionLocal", factory)
    assert recycle_bin_service.cleanup_expired_entries() == 1
    assert recycle_bin_service.cleanup_expired_entries() == 0

    db = factory()
    assert db.get(Brand, "brand-recycle-1") is None
    assert db.get(Material, "material-recycle-1") is not None
    db.close()
