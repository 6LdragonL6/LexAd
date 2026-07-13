from pathlib import Path

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


def test_bootstrap_imports_missing_pinduoduo_rules_and_is_idempotent(monkeypatch, tmp_path: Path):
    l4 = tmp_path / "L4_platforms" / "拼多多"
    l4.mkdir(parents=True)
    (l4 / "规则.txt").write_text("商家不得发布虚假宣传信息。不得夸大商品功效。", encoding="utf-8")
    l3 = tmp_path / "L3_cases"
    l3.mkdir()
    (l3 / "案例.txt").write_text("某品牌因虚假宣传引发消费者投诉和舆情风险，相关内容在多个社交平台传播后造成退款和信任危机。", encoding="utf-8")
    monkeypatch.setattr(knowledge_bootstrap, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(knowledge_bootstrap, "_L4_ROOT", tmp_path / "L4_platforms")
    monkeypatch.setattr(knowledge_bootstrap, "_L3_ROOT", l3)

    factory = _session_factory()
    db = factory()
    try:
        db.add(User(id="admin", username="admin", password="x", display_name="管理员", role=UserRole.admin, dept_name="管理部"))
        db.commit()
        summary = knowledge_bootstrap.bootstrap_builtin_knowledge(db)
        assert summary["platforms"] == 1
        assert summary["cases"] == 1
        rule_set = db.query(PlatformRuleSet).filter_by(platform_name="pinduoduo").one()
        assert db.query(PlatformRuleVersion).filter_by(rule_set_id=rule_set.id).count() == 1
        assert db.query(PublicOpinionLibraryVersion).one().event_count == 1
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
