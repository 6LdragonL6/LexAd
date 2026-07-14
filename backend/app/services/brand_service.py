import re
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.brand import Brand, BrandStatus
from app.models.material import Material, MaterialStatus
from app.models.review import LegalDecision, Review
from app.schemas.brand import (
    BrandCreate,
    BrandUpdate,
    BrandOut,
    BrandCreateResponse,
    BrandProfile,
    TopViolation,
    RecentReview,
    ApprovedMaterial,
)


def _normalize(name: str) -> str:
    """Remove leading/trailing whitespace, remove internal whitespace, lowercase."""
    return re.sub(r"\s+", "", name.strip()).lower()


def search_brands(db: Session, query: str = "", *, include_archived: bool = False) -> list[Brand]:
    q = query.strip()
    base_query = db.query(Brand).filter(Brand.deleted_at.is_(None))
    if not include_archived:
        base_query = base_query.filter(Brand.status == BrandStatus.active)
    if not q:
        return (
            base_query
            .order_by(Brand.name)
            .limit(50)
            .all()
        )
    normalized = _normalize(q)
    results = (
        base_query
        .order_by(Brand.name)
        .all()
    )
    matched = []
    for brand in results:
        name_norm = _normalize(brand.name)
        if normalized in name_norm or name_norm in normalized:
            matched.append(brand)
            continue
        for alias in brand.aliases or []:
            if normalized in _normalize(alias):
                matched.append(brand)
                break
    return matched[:50]


def find_by_normalized_name(db: Session, name: str, *, include_deleted: bool = False) -> Brand | None:
    normalized = _normalize(name)
    query = db.query(Brand)
    if not include_deleted:
        query = query.filter(Brand.deleted_at.is_(None))
    candidates = query.all()
    for brand in candidates:
        if _normalize(brand.name) == normalized:
            return brand
        for alias in brand.aliases or []:
            if _normalize(alias) == normalized:
                return brand
    return None


def create_brand(db: Session, data: BrandCreate, user_id: str) -> BrandCreateResponse:
    existing = find_by_normalized_name(db, data.name)
    if existing:
        return BrandCreateResponse(
            brand=BrandOut.model_validate(existing),
            created=False,
        )

    brand = Brand(
        name=data.name.strip(),
        industry=data.industry.strip() if data.industry else "",
        created_by_id=user_id,
    )
    db.add(brand)
    try:
        db.commit()
        db.refresh(brand)
    except Exception:
        db.rollback()
        existing = find_by_normalized_name(db, data.name)
        if existing:
            return BrandCreateResponse(
                brand=BrandOut.model_validate(existing),
                created=False,
            )
        raise
    return BrandCreateResponse(
        brand=BrandOut.model_validate(brand),
        created=True,
    )


def get_brand(db: Session, brand_id: str) -> Brand | None:
    return db.query(Brand).filter(Brand.id == brand_id, Brand.deleted_at.is_(None)).first()


def update_brand(db: Session, brand_id: str, data: BrandUpdate) -> Brand:
    brand = db.query(Brand).filter(Brand.id == brand_id, Brand.deleted_at.is_(None)).first()
    if not brand:
        raise ValueError("Brand not found")

    if data.name is not None:
        new_name = data.name.strip()
        if not new_name:
            raise ValueError("Brand name must not be blank")
        normalized_new = _normalize(new_name)
        if normalized_new != _normalize(brand.name):
            conflict = find_by_normalized_name(db, new_name)
            if conflict and conflict.id != brand.id:
                raise ValueError("Brand name conflict")
        data.name = new_name

    if data.industry is not None:
        data.industry = data.industry.strip()

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(brand, key, value)
    brand.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(brand)
    return brand


def _raw_text_preview(text: str, max_len: int = 100) -> str:
    if not text:
        return ""
    clean = text.replace("\n", " ").replace("\r", " ").strip()
    if len(clean) <= max_len:
        return clean
    return clean[:max_len] + "…"


def get_brand_profile(db: Session, brand_id: str) -> BrandProfile:
    brand = db.query(Brand).filter(Brand.id == brand_id, Brand.deleted_at.is_(None)).first()
    if not brand:
        raise ValueError("Brand not found")

    materials = db.query(Material).filter(Material.brand_id == brand_id, Material.deleted_at.is_(None)).all()
    material_ids = [m.id for m in materials]
    total_materials = len(materials)

    reviews = (
        db.query(Review).filter(Review.material_id.in_(material_ids), Review.task_status == "completed").all()
    ) if material_ids else []
    total_reviews = len(reviews)

    decided = [r for r in reviews if r.legal_decision is not None]
    decided_reviews = len(decided)

    approved = [r for r in decided if r.legal_decision == LegalDecision.approved]
    approved_count = len(approved)
    pass_rate = (approved_count / decided_reviews * 100) if decided_reviews > 0 else None

    versions = [m.current_version for m in materials]
    avg_versions = sum(versions) / len(versions) if versions else None

    violation_counter: Counter = Counter()
    for review in reviews:
        weight = 2 if review.legal_decision == LegalDecision.returned else 1
        ai = review.ai_result or {}
        for layer_key in ("layer1", "layer2", "layer3", "layer4"):
            layer = ai.get(layer_key, {})
            for rule in layer.get("matched_rules", []):
                key = (rule.get("rule_id", ""), rule.get("rule_text", ""))
                violation_counter[key] += weight

    top_10 = violation_counter.most_common(10)
    top_violations = [
        TopViolation(rule_id=rid, rule_text=rtext, count=cnt)
        for (rid, rtext), cnt in top_10
    ]

    sorted_completed = sorted(
        reviews, key=lambda r: r.completed_at or r.created_at, reverse=True
    )
    recent_reviews = [
        RecentReview(
            id=r.id,
            version=r.version,
            ai_risk_score=r.ai_risk_score,
            legal_decision=r.legal_decision.value if r.legal_decision else None,
            created_at=(r.created_at.isoformat() if r.created_at else ""),
        )
        for r in sorted_completed[:5]
    ]

    approved_materials = [
        ApprovedMaterial(
            id=m.id,
            name=m.name,
            raw_text_preview=_raw_text_preview(m.raw_text),
        )
        for m in materials
        if m.status == MaterialStatus.approved
    ][:10]

    return BrandProfile(
        brand=BrandOut.model_validate(brand),
        total_materials=total_materials,
        total_reviews=total_reviews,
        decided_reviews=decided_reviews,
        approved_count=approved_count,
        pass_rate=pass_rate,
        avg_versions=avg_versions,
        top_violations=top_violations,
        recent_reviews=recent_reviews,
        approved_materials=approved_materials,
    )
