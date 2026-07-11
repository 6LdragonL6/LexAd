from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.material import Material, MaterialStatus
from app.models.user import User, UserRole
from app.schemas.material import MaterialSubmit, MaterialUpdate


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
    db.commit()
    db.refresh(material)
    return material


def _merge_texts(extracted: str, form_text: str) -> str:
    # The form text is the user's final, editable preview. Prefer it to avoid
    # appending the same extracted content a second time.
    return form_text.strip() or extracted.strip()


def get_material(db: Session, material_id: str) -> Material | None:
    return db.query(Material).filter(Material.id == material_id).first()


def list_materials(db: Session, user: User) -> list[Material]:
    query = db.query(Material).filter(Material.status != MaterialStatus.archived)
    if user.role == UserRole.marketing:
        query = query.filter(Material.submitter_id == user.id)
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
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        return None

    if material.status == MaterialStatus.returned:
        changed = False
        if data.raw_text is not None and data.raw_text != material.raw_text:
            changed = True
        if data.industry is not None and data.industry != material.industry:
            changed = True
        if data.platforms is not None and data.platforms != material.platforms:
            changed = True
        if changed:
            material.current_version += 1

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(material, key, value)
    material.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(material)
    return material


def get_material_versions(db: Session, material_id: str) -> list[dict]:
    from app.models.review import Review
    from app.models.material import MaterialSubmissionSnapshot
    reviews = db.query(Review).filter(Review.material_id == material_id).order_by(Review.version.desc()).all()
    versions = []
    for r in reviews:
        snapshot = db.get(MaterialSubmissionSnapshot, r.submission_snapshot_id) if r.submission_snapshot_id else None
        versions.append({
            "version": r.version,
            "risk_score": r.ai_risk_score,
            "task_status": r.task_status,
            "legal_decision": r.legal_decision.value if r.legal_decision else None,
            "return_reasons": r.return_reasons,
            "legal_notes": r.legal_notes,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "created_at": r.created_at.isoformat(),
            "version_label": f"第{r.version}次提交",
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
