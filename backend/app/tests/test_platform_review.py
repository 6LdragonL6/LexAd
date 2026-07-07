from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.engine.layer4_platform import run_platform_review
from app.models.knowledge import PlatformRuleSet, PlatformRuleStatus, PlatformRuleVersion, ReviewModuleStatus
from app.models.material import Material, MaterialStatus
from app.models.review import Review
from app.models.user import User, UserRole
from app.schemas.review import LayerResult
from app.services import review_service


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _seed_user_material_and_platform_rule(factory):
    db = factory()
    user = User(
        id="user-1",
        username="market-test",
        password="not-used",
        display_name="市场测试",
        role=UserRole.marketing,
        dept_name="市场部",
    )
    material = Material(
        id="material-1",
        name="测试物料",
        raw_text="本产品是全网最低价，支持极速发货。",
        industry="食品",
        platforms=["douyin"],
        submitter_id=user.id,
    )
    rule_set = PlatformRuleSet(
        id="rule-set-1",
        platform_name="douyin",
        display_name="抖音",
    )
    version = PlatformRuleVersion(
        id="platform-version-1",
        rule_set_id=rule_set.id,
        version_label="2026-07",
        raw_text="不得宣传全网最低价",
        structured_rules=[
            {
                "rule_id": "price-001",
                "text": "不得宣传全网最低价",
                "keywords": ["全网最低价"],
                "risk_level": "平台规则",
            }
        ],
        status=PlatformRuleStatus.active,
        effective_at=datetime.now(timezone.utc),
        imported_by_id=user.id,
        activated_by_id=user.id,
        activated_at=datetime.now(timezone.utc),
    )
    db.add_all([user, material, rule_set, version])
    db.commit()
    db.close()


def test_platform_review_matches_active_platform_rule():
    factory = _session_factory()
    _seed_user_material_and_platform_rule(factory)
    db = factory()
    try:
        result = run_platform_review("本产品是全网最低价", ["douyin"], db)
        assert result.platform_rule_version_ids == ["platform-version-1"]
        assert result.unavailable_platforms == []
        assert len(result.matched_rules) == 1
        assert result.matched_rules[0].rule_id == "L4-platform-version-1-price-001"
        assert result.matched_rules[0].source_law == "抖音 2026-07"
    finally:
        db.close()


def test_platform_review_reports_missing_active_rules_without_false_pass():
    factory = _session_factory()
    db = factory()
    try:
        result = run_platform_review("普通文案", ["unknown-platform"], db)
        assert result.matched_rules == []
        assert result.platform_rule_version_ids == []
        assert result.unavailable_platforms == ["unknown-platform"]
        assert "暂无规则集" in result.explanations[0]
    finally:
        db.close()


def test_review_task_snapshots_platform_rule_versions(monkeypatch):
    factory = _session_factory()
    _seed_user_material_and_platform_rule(factory)
    monkeypatch.setattr(review_service, "SessionLocal", factory)

    def fake_semantic_review(_text, _industry):
        return LayerResult(layer="语义推理", matched_rules=[], explanations=[])

    import app.engine.layer2_semantic as layer2_semantic

    monkeypatch.setattr(layer2_semantic, "run_semantic_review", fake_semantic_review)

    db = factory()
    review, _ = review_service.create_ai_review(db, "material-1")
    db.close()

    review_service.execute_ai_review(review.id)

    db = factory()
    try:
        stored = db.query(Review).filter(Review.id == review.id).one()
        material = db.query(Material).filter(Material.id == "material-1").one()
        assert stored.task_status == "completed"
        assert stored.platform_rule_version_ids == ["platform-version-1"]
        assert stored.legal_module_status == ReviewModuleStatus.succeeded
        assert stored.public_opinion_module_status == ReviewModuleStatus.unavailable
        assert stored.ai_result["layer4"]["matched_rules"][0]["rule_id"] == "L4-platform-version-1-price-001"
        assert material.status == MaterialStatus.pending_legal
    finally:
        db.close()


def test_chinese_platform_name_matches_douyin_ruleset():
    factory = _session_factory()
    _seed_user_material_and_platform_rule(factory)
    db = factory()
    try:
        result = run_platform_review("本产品是全网最低价", ["抖音"], db)
        assert result.platform_rule_version_ids == ["platform-version-1"]
        assert result.unavailable_platforms == []
        assert len(result.matched_rules) == 1
        assert result.matched_rules[0].source_law == "抖音 2026-07"
        assert "抖音" in result.platform_version_labels["platform-version-1"]
    finally:
        db.close()


def test_platform_alias_xiaohongshu_matches_xhs():
    factory = _session_factory()
    db = factory()
    try:
        user = User(
            id="user-2",
            username="market-test-2",
            password="not-used",
            display_name="市场测试2",
            role=UserRole.marketing,
            dept_name="市场部",
        )
        rule_set = PlatformRuleSet(
            id="rule-set-xhs",
            platform_name="xhs",
            display_name="小红书",
        )
        version = PlatformRuleVersion(
            id="platform-version-xhs",
            rule_set_id=rule_set.id,
            version_label="2026-Q3",
            raw_text="小红书社区规则",
            structured_rules=[
                {
                    "rule_id": "xhs-001",
                    "text": "不得使用夸大宣传",
                    "keywords": ["夸大宣传"],
                    "risk_level": "平台规则",
                }
            ],
            status=PlatformRuleStatus.active,
            effective_at=datetime.now(timezone.utc),
            imported_by_id=user.id,
            activated_by_id=user.id,
            activated_at=datetime.now(timezone.utc),
        )
        db.add_all([user, rule_set, version])
        db.commit()
        result = run_platform_review("本产品夸大宣传", ["小红书"], db)
        assert result.platform_rule_version_ids == ["platform-version-xhs"]
        assert result.unavailable_platforms == []
        assert "小红书" in result.platform_version_labels["platform-version-xhs"]
    finally:
        db.close()


def test_platform_rule_set_exists_but_no_active_version():
    factory = _session_factory()
    db = factory()
    try:
        user = User(
            id="user-3",
            username="market-test-3",
            password="not-used",
            display_name="市场测试3",
            role=UserRole.marketing,
            dept_name="市场部",
        )
        rule_set = PlatformRuleSet(
            id="rule-set-no-active",
            platform_name="weibo",
            display_name="微博",
        )
        version = PlatformRuleVersion(
            id="platform-version-draft",
            rule_set_id=rule_set.id,
            version_label="2026-draft",
            raw_text="微博平台规则草案",
            structured_rules=[],
            status=PlatformRuleStatus.draft,
            imported_by_id=user.id,
        )
        db.add_all([user, rule_set, version])
        db.commit()
        result = run_platform_review("普通文案", ["微博"], db)
        assert result.matched_rules == []
        assert result.platform_rule_version_ids == []
        assert result.unavailable_platforms == ["微博"]
        assert "已有规则集，但暂无生效版本" in result.explanations[0]
    finally:
        db.close()


def test_unavailable_platform_shows_chinese_name_not_internal_id():
    factory = _session_factory()
    db = factory()
    try:
        result = run_platform_review("普通文案", ["抖音"], db)
        assert result.unavailable_platforms == ["抖音"]
        assert "抖音" in result.explanations[0]
    finally:
        db.close()


def test_platform_version_labels_populated():
    factory = _session_factory()
    _seed_user_material_and_platform_rule(factory)
    db = factory()
    try:
        result = run_platform_review("本产品是全网最低价", ["抖音"], db)
        assert "platform-version-1" in result.platform_version_labels
        assert result.platform_version_labels["platform-version-1"] == "抖音 / 2026-07"
    finally:
        db.close()
