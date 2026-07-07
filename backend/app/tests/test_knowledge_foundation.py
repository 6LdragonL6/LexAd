"""Knowledge foundation regression tests for v0.4.2."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import require_admin
from app.db.base import Base
from app.models.knowledge import (
    PlatformRuleSet,
    PlatformRuleStatus,
    PlatformRuleVersion,
    PublicOpinionEvent,
    PublicOpinionEventStatus,
    ReviewModuleStatus,
)
from app.models.material import Material
from app.models.review import Review
from app.models.user import User, UserRole


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _user(user_id: str, role: UserRole = UserRole.admin) -> User:
    return User(
        id=user_id,
        username=f"user-{user_id}",
        password="not-used",
        display_name="Test User",
        role=role,
        dept_name="Test",
    )


def test_public_opinion_event_status_transitions_and_delete_rule():
    event = PublicOpinionEvent(
        title="case",
        source_text="source",
        consequence_text="impact",
        created_by_id="admin-1",
    )

    assert event.can_delete() is True
    assert event.can_transition_to(PublicOpinionEventStatus.ai_processing) is True
    event.transition_to(PublicOpinionEventStatus.ai_processing)
    event.transition_to(PublicOpinionEventStatus.pending_review)
    event.transition_to(PublicOpinionEventStatus.published)

    assert event.can_delete() is False
    assert event.can_transition_to(PublicOpinionEventStatus.draft) is False
    with pytest.raises(ValueError, match="Invalid public opinion event transition"):
        event.transition_to(PublicOpinionEventStatus.draft)

    event.transition_to(PublicOpinionEventStatus.archived)
    event.transition_to(PublicOpinionEventStatus.published)
    assert event.status == PublicOpinionEventStatus.published


def test_platform_rule_version_effective_window_requires_active_status():
    now = datetime.now(timezone.utc)
    rule_set = PlatformRuleSet(platform_name="douyin", display_name="抖音")
    version = PlatformRuleVersion(
        rule_set_id=rule_set.id,
        version_label="2026-07",
        raw_text="rule",
        structured_rules=[],
        imported_by_id="admin-1",
        status=PlatformRuleStatus.pending_effective,
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
    )

    assert version.is_effective_at(now) is False

    version.status = PlatformRuleStatus.active
    assert version.is_effective_at(now) is True
    assert version.is_effective_at(now - timedelta(days=2)) is False
    assert version.is_effective_at(now + timedelta(days=2)) is False


def test_review_has_independent_module_statuses_and_knowledge_snapshots():
    factory = _session_factory()
    db = factory()
    admin = _user("admin-1")
    material = Material(
        id="material-1",
        name="Material",
        raw_text="copy",
        industry="food",
        platforms=["douyin"],
        submitter_id=admin.id,
    )
    review = Review(
        id="review-1",
        material_id=material.id,
        platform_rule_version_ids=["platform-version-1"],
        public_opinion_library_version_id=None,
    )

    db.add_all([admin, material, review])
    db.commit()

    stored = db.query(Review).filter(Review.id == "review-1").one()
    assert stored.legal_module_status == ReviewModuleStatus.pending
    assert stored.public_opinion_module_status == ReviewModuleStatus.pending
    assert stored.platform_rule_version_ids == ["platform-version-1"]
    assert stored.public_opinion_result == {}
    assert stored.legal_module_retry_count == 0
    assert stored.public_opinion_module_retry_count == 0
    db.close()


def test_admin_dependency_remains_backend_enforced():
    admin = _user("admin-1", UserRole.admin)
    marketing = _user("marketing-1", UserRole.marketing)

    assert require_admin(admin) is admin
    with pytest.raises(HTTPException) as exc_info:
        require_admin(marketing)
    assert exc_info.value.status_code == 403
