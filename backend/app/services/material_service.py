from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.material import Material, MaterialStatus
from app.models.user import User, UserRole
from app.schemas.material import MaterialSubmit, MaterialUpdate


def create_material(db: Session, data: MaterialSubmit, submitter_id: str) -> Material:
    material = Material(
        name=data.name,
        industry=data.industry,
        platforms=data.platforms,
        material_type=data.material_type,
        raw_text=data.raw_text,
        priority=data.priority,
        deadline=data.deadline,
        status=MaterialStatus.draft,
        submitter_id=submitter_id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def get_material(db: Session, material_id: str) -> Material | None:
    return db.query(Material).filter(Material.id == material_id).first()


def list_materials(db: Session, user: User) -> list[Material]:
    query = db.query(Material)
    if user.role == UserRole.marketing:
        query = query.filter(Material.submitter_id == user.id)
    return query.order_by(Material.created_at.desc()).all()


def update_material(db: Session, material_id: str, data: MaterialUpdate) -> Material | None:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(material, key, value)
    material.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(material)
    return material


def get_material_versions(db: Session, material_id: str) -> list[dict]:
    from app.models.review import Review
    reviews = db.query(Review).filter(Review.material_id == material_id).order_by(Review.version.desc()).all()
    return [{"version": r.version, "risk_score": r.ai_risk_score, "decision": r.legal_decision.value if r.legal_decision else None, "created_at": r.created_at.isoformat()} for r in reviews]
