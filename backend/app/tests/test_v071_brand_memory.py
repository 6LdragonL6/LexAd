from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.brand import Brand, BrandIndustry
from app.models.material import Material, MaterialStatus
from app.models.review import LegalDecision, Review
from app.models.user import User, UserRole
from app.services import brand_service


def _seed_brand(db: Session) -> tuple[User, Brand]:
    user = User(
        id="owner",
        username="owner",
        password="x",
        display_name="品牌负责人",
        role=UserRole.admin,
        dept_name="管理部",
    )
    brand = Brand(id="brand", name="记忆品牌", created_by_id=user.id)
    db.add_all([user, brand, BrandIndustry(brand_id=brand.id, industry="食品", created_by_id=user.id)])
    db.commit()
    return user, brand


def _add_decided_review(
    db: Session,
    *,
    owner: User,
    brand: Brand,
    index: int,
    decision: LegalDecision,
    suggestions: list[str] | None = None,
) -> None:
    created_at = datetime(2026, 7, 15, tzinfo=timezone.utc) + timedelta(minutes=index)
    material = Material(
        id=f"material-{index}",
        name=f"物料{index}",
        display_name=f"物料{index}",
        industry="食品",
        submitter_id=owner.id,
        brand_id=brand.id,
        current_version=1 if index == 1 else 2,
        status=MaterialStatus.approved if decision == LegalDecision.approved else MaterialStatus.returned,
        created_at=created_at,
    )
    review = Review(
        id=f"review-{index}",
        material_id=material.id,
        version=material.current_version,
        task_status="completed",
        legal_compliance_score=88 if decision == LegalDecision.approved else 42,
        public_opinion_safety_score=90 if decision == LegalDecision.approved else 45,
        ai_result={
            "layer1": {
                "matched_rules": [
                    {"rule_id": "risk-1", "rule_text": "绝对化表达"},
                ]
            },
            "suggestions": suggestions or [],
        },
        legal_decision=decision,
        completed_at=created_at,
        reviewed_at=created_at,
        created_at=created_at,
    )
    db.add_all([material, review])


def test_brand_memory_without_history_stays_collecting():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        _, brand = _seed_brand(db)

        memory = brand_service.get_brand_profile(db, brand.id).memory_impression

        assert memory.status == "collecting"
        assert memory.headline == "样本积累中"
        assert memory.completed_review_count == 0
        assert memory.decided_review_count == 0
        assert memory.industries == ["食品"]


def test_brand_memory_builds_stable_deterministic_summary_and_deduplicates_suggestions():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        owner, brand = _seed_brand(db)
        _add_decided_review(
            db,
            owner=owner,
            brand=brand,
            index=1,
            decision=LegalDecision.approved,
            suggestions=["  删除绝对化表述  ", "删除绝对化表述"],
        )
        _add_decided_review(
            db,
            owner=owner,
            brand=brand,
            index=2,
            decision=LegalDecision.approved,
            suggestions=["删除绝对化表述", "补充证明材料"],
        )
        _add_decided_review(
            db,
            owner=owner,
            brand=brand,
            index=3,
            decision=LegalDecision.approved,
            suggestions=["删除绝对化表述"],
        )
        db.commit()

        memory = brand_service.get_brand_profile(db, brand.id).memory_impression

        assert memory.status == "stable"
        assert memory.headline == "整体较稳定"
        assert memory.recent_decisions.approved == 3
        assert memory.recent_decisions.conditional == 0
        assert memory.recent_decisions.returned == 0
        assert memory.revision_tendency == "通常需要一轮以上调整"
        assert [(item.text, item.count) for item in memory.frequent_risks] == [("绝对化表达", 3)]
        assert [(item.text, item.count) for item in memory.common_suggestions] == [
            ("删除绝对化表述", 3),
            ("补充证明材料", 1),
        ]


def test_brand_memory_flags_repeated_recent_returns_for_attention():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        owner, brand = _seed_brand(db)
        for index in range(1, 4):
            _add_decided_review(
                db,
                owner=owner,
                brand=brand,
                index=index,
                decision=LegalDecision.returned,
                suggestions=["修改风险表述"],
            )
        db.commit()

        memory = brand_service.get_brand_profile(db, brand.id).memory_impression

        assert memory.status == "attention"
        assert memory.headline == "需要重点关注"
        assert memory.recent_decisions.returned == 3
        assert memory.frequent_risks[0].count == 6
