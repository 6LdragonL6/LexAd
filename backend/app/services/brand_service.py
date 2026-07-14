import re
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.engine.industry import split_industries, validate_industries
from app.models.brand import (
    Brand,
    BrandIndustry,
    BrandIndustrySuggestion,
    BrandIndustrySuggestionStatus,
    BrandStatus,
)
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
    BrandIndustrySuggestionOut,
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
        db.flush()
        requested_industries = validate_industries([*data.industries, *split_industries(data.industry)])
        for industry in requested_industries:
            db.add(BrandIndustry(brand_id=brand.id, industry=industry, created_by_id=user_id))
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


def update_brand(db: Session, brand_id: str, data: BrandUpdate, actor_id: str | None = None) -> Brand:
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

    update_data = data.model_dump(exclude_unset=True, exclude={"industries"})
    for key, value in update_data.items():
        setattr(brand, key, value)
    if data.industries is not None:
        _replace_brand_industries(db, brand, data.industries, actor_id or brand.created_by_id)
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


def get_brand_profile(db: Session, brand_id: str, *, include_suggestions: bool = False) -> BrandProfile:
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

    industry_suggestions: list[BrandIndustrySuggestionOut] = []
    if include_suggestions:
        suggestions = (
            db.query(BrandIndustrySuggestion)
            .filter(BrandIndustrySuggestion.brand_id == brand_id)
            .order_by(BrandIndustrySuggestion.status, BrandIndustrySuggestion.last_seen_at.desc())
            .all()
        )
        latest_ids = [item.latest_material_id for item in suggestions if item.latest_material_id]
        latest_materials = {
            item.id: item for item in db.query(Material).filter(Material.id.in_(latest_ids)).all()
        } if latest_ids else {}
        industry_suggestions = [
            BrandIndustrySuggestionOut(
                id=item.id,
                industry=item.industry,
                status=item.status.value,
                first_material_id=item.first_material_id,
                latest_material_id=item.latest_material_id,
                latest_material_name=(
                    (latest_materials[item.latest_material_id].display_name or latest_materials[item.latest_material_id].name)
                    if item.latest_material_id in latest_materials else ""
                ),
                occurrence_count=item.occurrence_count,
                first_seen_at=item.first_seen_at,
                last_seen_at=item.last_seen_at,
                reviewed_at=item.reviewed_at,
            )
            for item in suggestions
        ]

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
        industry_suggestions=industry_suggestions,
    )


def _replace_brand_industries(db: Session, brand: Brand, industries: list[str], actor_id: str) -> None:
    requested = validate_industries(industries)
    existing = {link.industry: link for link in db.query(BrandIndustry).filter(BrandIndustry.brand_id == brand.id).all()}
    requested_set = set(requested)
    for industry, link in existing.items():
        if industry not in requested_set:
            db.delete(link)
    for industry in requested:
        if industry not in existing:
            db.add(BrandIndustry(brand_id=brand.id, industry=industry, created_by_id=actor_id))
        suggestion = db.query(BrandIndustrySuggestion).filter(
            BrandIndustrySuggestion.brand_id == brand.id,
            BrandIndustrySuggestion.industry == industry,
        ).first()
        if suggestion:
            suggestion.status = BrandIndustrySuggestionStatus.accepted
            suggestion.reviewed_by_id = actor_id
            suggestion.reviewed_at = datetime.now(timezone.utc)


def set_brand_industries(db: Session, brand_id: str, industries: list[str], actor_id: str) -> Brand:
    brand = get_brand(db, brand_id)
    if not brand:
        raise ValueError("Brand not found")
    _replace_brand_industries(db, brand, industries, actor_id)
    brand.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.expire(brand, ["industry_links"])
    db.refresh(brand)
    return brand


def record_material_industries(db: Session, material: Material) -> None:
    if not material.brand_id:
        return
    industries = validate_industries(material.industry)
    accepted = {
        row.industry for row in db.query(BrandIndustry).filter(BrandIndustry.brand_id == material.brand_id).all()
    }
    now = datetime.now(timezone.utc)
    for industry in industries:
        if industry in accepted:
            continue
        suggestion = db.query(BrandIndustrySuggestion).filter(
            BrandIndustrySuggestion.brand_id == material.brand_id,
            BrandIndustrySuggestion.industry == industry,
        ).first()
        if suggestion is None:
            db.add(BrandIndustrySuggestion(
                brand_id=material.brand_id,
                industry=industry,
                status=BrandIndustrySuggestionStatus.pending,
                first_material_id=material.id,
                latest_material_id=material.id,
                occurrence_count=1,
                first_seen_at=now,
                last_seen_at=now,
            ))
            continue
        suggestion.latest_material_id = material.id
        suggestion.last_seen_at = now
        suggestion.occurrence_count += 1
        if suggestion.status == BrandIndustrySuggestionStatus.accepted:
            suggestion.status = BrandIndustrySuggestionStatus.pending
            suggestion.reviewed_by_id = None
            suggestion.reviewed_at = None


def review_industry_suggestion(
    db: Session,
    brand_id: str,
    suggestion_id: str,
    action: str,
    actor_id: str,
) -> BrandIndustrySuggestion:
    suggestion = db.query(BrandIndustrySuggestion).filter(
        BrandIndustrySuggestion.id == suggestion_id,
        BrandIndustrySuggestion.brand_id == brand_id,
    ).first()
    if not suggestion:
        raise ValueError("Industry suggestion not found")
    now = datetime.now(timezone.utc)
    if action == "accept":
        existing = db.query(BrandIndustry).filter(
            BrandIndustry.brand_id == brand_id,
            BrandIndustry.industry == suggestion.industry,
        ).first()
        if not existing:
            db.add(BrandIndustry(brand_id=brand_id, industry=suggestion.industry, created_by_id=actor_id))
        suggestion.status = BrandIndustrySuggestionStatus.accepted
    elif action == "ignore":
        suggestion.status = BrandIndustrySuggestionStatus.ignored
    elif action == "restore":
        suggestion.status = BrandIndustrySuggestionStatus.pending
    else:
        raise ValueError("Unsupported suggestion action")
    suggestion.reviewed_by_id = actor_id
    suggestion.reviewed_at = now
    db.commit()
    db.refresh(suggestion)
    return suggestion
