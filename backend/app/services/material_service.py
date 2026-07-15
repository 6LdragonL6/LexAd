from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.material import Material, MaterialStatus, MaterialSubmissionSnapshot
from app.models.user import User, UserRole
from app.schemas.material import MaterialSubmit, MaterialUpdate, MaterialResubmit


def create_material(
    db: Session,
    data: MaterialSubmit,
    submitter_id: str,
    extracted_text: str = "",
    brand_id: str | None = None,
) -> Material:
    final_text = _merge_texts(extracted_text, data.raw_text)
    material = Material(
        name=data.name,
        display_name=data.name,
        industry=data.industry,
        platforms=data.platforms,
        material_type=data.material_type,
        raw_text=final_text,
        priority=data.priority,
        deadline=data.deadline,
        status=MaterialStatus.draft,
        submitter_id=submitter_id,
        brand_id=brand_id,
    )
    db.add(material)
    db.flush()
    from app.services import brand_service
    brand_service.record_material_industries(db, material)
    db.commit()
    db.refresh(material)
    return material


def _merge_texts(extracted: str, form_text: str) -> str:
    # The form text is the user's final, editable preview. Prefer it to avoid
    # appending the same extracted content a second time.
    return form_text.strip() or extracted.strip()


def get_material(db: Session, material_id: str) -> Material | None:
    return db.query(Material).filter(Material.id == material_id, Material.deleted_at.is_(None)).first()


def list_materials(db: Session, user: User) -> list[Material]:
    query = db.query(Material).filter(Material.deleted_at.is_(None))
    if user.role == UserRole.marketing:
        query = query.filter(
            Material.submitter_id == user.id,
            Material.status != MaterialStatus.archived,
        )
    elif user.role == UserRole.legal:
        query = query.filter(
            Material.status.in_(
                [
                    MaterialStatus.pending_legal,
                    MaterialStatus.in_legal_review,
                    MaterialStatus.approved,
                    MaterialStatus.conditional_approved,
                    MaterialStatus.returned,
                ]
            )
        )
    return query.order_by(Material.created_at.desc()).all()


def update_material(db: Session, material_id: str, data: MaterialUpdate) -> Material | None:
    material = db.query(Material).filter(Material.id == material_id, Material.deleted_at.is_(None)).first()
    if not material:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(material, key, value)
    material.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(material)
    return material


def create_resubmission(db: Session, material: Material, data: MaterialResubmit):
    from app.models.brand import Brand, BrandStatus
    from app.models.knowledge import ReviewModuleStatus
    from app.models.review import Review
    from app.services import brand_service

    locked_material = (
        db.query(Material)
        .filter(Material.id == material.id, Material.deleted_at.is_(None))
        .with_for_update()
        .first()
    )
    if locked_material is None:
        raise ValueError("物料不存在")
    material = locked_material
    if material.status != MaterialStatus.returned:
        raise ValueError("只有已退回的物料可以重新提交")
    if material.brand_id:
        brand = db.query(Brand).filter(
            Brand.id == material.brand_id,
            Brand.status == BrandStatus.active,
            Brand.deleted_at.is_(None),
        ).first()
        if not brand:
            raise ValueError("原品牌已归档或删除，请联系管理员恢复后再提交")

    material.current_version += 1
    material.name = data.name
    material.raw_text = data.raw_text
    material.industry = data.industry
    material.platforms = data.platforms
    material.material_type = data.material_type
    material.priority = data.priority
    material.deadline = data.deadline
    material.status = MaterialStatus.ai_reviewing
    material.updated_at = datetime.now(timezone.utc)

    snapshot = MaterialSubmissionSnapshot(
        material_id=material.id,
        version=material.current_version,
        name=material.name,
        industry=material.industry,
        platforms=material.platforms,
        material_type=material.material_type,
        raw_text=material.raw_text,
        priority=material.priority.value if hasattr(material.priority, "value") else material.priority,
        deadline=material.deadline,
    )
    db.add(snapshot)
    db.flush()
    review = Review(
        material_id=material.id,
        submission_snapshot_id=snapshot.id,
        version=material.current_version,
        legal_compliance_score=0,
        public_opinion_safety_score=None,
        ai_result={},
        task_status="processing",
        legal_module_status=ReviewModuleStatus.pending,
        public_opinion_module_status=ReviewModuleStatus.pending,
    )
    db.add(review)
    brand_service.record_material_industries(db, material)
    db.commit()
    db.refresh(review)
    return review


def get_material_versions(db: Session, material_id: str) -> list[dict]:
    from app.models.review import Review
    reviews = db.query(Review).filter(Review.material_id == material_id).order_by(Review.version.desc()).all()
    versions = []
    for r in reviews:
        snapshot = r.submission or (db.get(MaterialSubmissionSnapshot, r.submission_snapshot_id) if r.submission_snapshot_id else None)
        versions.append({
            "review_id": r.id,
            "version": r.version,
            "legal_compliance_score": r.legal_compliance_score,
            "public_opinion_safety_score": r.public_opinion_safety_score,
            "task_status": r.task_status,
            "legal_decision": r.legal_decision.value if r.legal_decision else None,
            "return_reasons": r.return_reasons,
            "legal_notes": r.legal_notes,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "created_at": r.created_at.isoformat(),
            "version_label": f"第{r.version}次提交",
            "legal_review_label": f"第{r.version}次法务审核" if r.legal_decision else "尚未法务审核",
            "snapshot_complete": bool(snapshot),
            "submission": {
                "name": snapshot.name,
                "raw_text": snapshot.raw_text,
                "industry": snapshot.industry,
                "platforms": snapshot.platforms,
                "material_type": snapshot.material_type,
                "priority": snapshot.priority,
                "deadline": snapshot.deadline.isoformat() if snapshot.deadline else None,
            } if snapshot else None,
        })
    return versions
