from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.engine.layer4_platform import run_platform_review
from app.models.knowledge import KnowledgeImportJob, PlatformRuleSet, PlatformRuleVersion, PublicOpinionLibraryVersion
from app.models.user import User, UserRole
from app.services import knowledge_bootstrap


def _session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def test_bootstrap_imports_repository_rules_and_real_cases_idempotently():
    factory = _session_factory()
    db = factory()
    try:
        db.add(User(id="admin", username="admin", password="x", display_name="管理员", role=UserRole.admin, dept_name="管理部"))
        db.commit()
        summary = knowledge_bootstrap.bootstrap_builtin_knowledge(db)
        assert summary["platforms"] >= 1
        assert summary["cases"] == 33
        rule_set = db.query(PlatformRuleSet).filter_by(platform_name="pinduoduo").one()
        assert db.query(PlatformRuleVersion).filter_by(rule_set_id=rule_set.id).count() == 1
        assert db.query(PublicOpinionLibraryVersion).one().event_count == 33
        assert db.query(KnowledgeImportJob).count() == 1
        result = run_platform_review("这是一段虚假宣传文案", ["pdd"], db)
        assert result.platform_rule_version_ids
        assert result.matched_rules

        second = knowledge_bootstrap.bootstrap_builtin_knowledge(db)
        assert second["platforms"] == 0
        assert db.query(PlatformRuleVersion).filter_by(rule_set_id=rule_set.id).count() == 1
        assert db.query(KnowledgeImportJob).count() == 1
    finally:
        db.close()
