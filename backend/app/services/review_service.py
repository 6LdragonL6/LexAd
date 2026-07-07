from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import case, func
from app.models.material import Material, MaterialStatus
from app.models.knowledge import ReviewModuleStatus
from app.models.review import Review, LegalDecision
from app.models.user import User, UserRole
from app.schemas.review import LegalDecisionRequest
from app.engine.pipeline import run_review_pipeline
from app.db.session import SessionLocal


def create_ai_review(db: Session, material_id: str) -> tuple[Review, bool]:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise ValueError("Material not found")

    running = (
        db.query(Review)
        .filter(Review.material_id == material_id, Review.task_status == "processing")
        .order_by(Review.created_at.desc())
        .first()
    )
    if running:
        is_stale = datetime.now(timezone.utc) - _as_utc(running.created_at) > timedelta(minutes=15)
        if not is_stale:
            return running, False
        running.task_status = "failed"
        running.error_message = "上一次审查任务因服务中断未完成，请重新审查"
        running.completed_at = datetime.now(timezone.utc)
        material.status = MaterialStatus.draft
        db.commit()

    if material.status not in (MaterialStatus.draft, MaterialStatus.returned):
        raise ValueError("当前物料状态不允许重新发起 AI 审查")

    material.status = MaterialStatus.ai_reviewing
    review = Review(
        material_id=material_id,
        version=material.current_version,
        ai_risk_score=0,
        ai_result={},
        task_status="processing",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review, True


def execute_ai_review(review_id: str) -> None:
    """Execute a review after the HTTP response using an independent DB session."""
    db = SessionLocal()
    try:
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review or review.task_status != "processing":
            return
        material = db.query(Material).filter(Material.id == review.material_id).first()
        if not material:
            raise ValueError("物料不存在")

        review.started_at = datetime.now(timezone.utc)
        db.commit()

        engine_result = run_review_pipeline(
            material.raw_text,
            material.industry,
            material.platforms,
            db,
        )
        review.ai_risk_score = engine_result.risk_score
        review.ai_result = engine_result.model_dump()
        review.platform_rule_version_ids = engine_result.platform_rule_version_ids
        review.legal_module_status = ReviewModuleStatus.succeeded
        review.legal_module_error = None
        review.legal_module_completed_at = datetime.now(timezone.utc)
        review.public_opinion_module_status = ReviewModuleStatus.unavailable
        review.public_opinion_module_error = "舆情风险分析将在 v0.4.2 后续阶段接入"
        review.task_status = "completed"
        review.error_message = None
        review.completed_at = datetime.now(timezone.utc)
        material.status = MaterialStatus.pending_legal
        db.commit()
    except Exception as exc:
        db.rollback()
        review = db.query(Review).filter(Review.id == review_id).first()
        if review:
            material = db.query(Material).filter(Material.id == review.material_id).first()
            review.task_status = "failed"
            review.error_message = _safe_error_message(exc)
            review.legal_module_status = ReviewModuleStatus.failed
            review.legal_module_error = review.error_message
            review.legal_module_completed_at = datetime.now(timezone.utc)
            review.completed_at = datetime.now(timezone.utc)
            if material and material.status == MaterialStatus.ai_reviewing:
                material.status = MaterialStatus.draft
            db.commit()
    finally:
        db.close()


def _safe_error_message(exc: Exception) -> str:
    text = str(exc).strip()
    if not text:
        return "审查服务暂时不可用，请稍后重试"
    if "api key" in text.lower():
        return "AI 服务尚未正确配置，请联系管理员检查 API Key"
    return f"审查失败：{text[:180]}"


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def get_review(db: Session, review_id: str) -> Review | None:
    return db.query(Review).filter(Review.id == review_id).first()


def get_latest_review_by_material(db: Session, material_id: str) -> Review | None:
    return (
        db.query(Review)
        .filter(Review.material_id == material_id)
        .order_by(Review.version.desc(), Review.created_at.desc())
        .first()
    )


def submit_legal_decision(db: Session, review_id: str, data: LegalDecisionRequest, reviewer: User) -> Review:
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise ValueError("Review not found")
    if review.task_status != "completed":
        raise ValueError("AI 审查尚未完成")
    if review.legal_decision is not None:
        raise ValueError("该审查已经提交法务决定，不能重复覆盖")

    material = db.query(Material).filter(Material.id == review.material_id).first()
    review.legal_decision = LegalDecision(data.decision)
    review.legal_notes = data.notes
    review.return_reasons = data.return_reasons
    review.reviewer_id = reviewer.id
    review.reviewed_at = datetime.now(timezone.utc)

    if data.decision == "approved":
        material.status = MaterialStatus.approved
    elif data.decision in ("returned", "conditional"):
        material.status = MaterialStatus.returned
    db.commit()
    db.refresh(review)
    return review


def get_legal_queue(db: Session, user: User) -> list[dict]:
    query = db.query(Review).join(Material, Review.material_id == Material.id)
    latest_review_created_at = (
        db.query(func.max(Review.created_at))
        .filter(Review.material_id == Material.id)
        .correlate(Material)
        .scalar_subquery()
    )
    query = query.filter(Review.created_at == latest_review_created_at)

    if user.role == UserRole.marketing:
        query = query.filter(Material.submitter_id == user.id)
    else:
        query = query.filter(
            Review.task_status == "completed",
            Review.legal_decision.is_(None),
            Material.status.in_([MaterialStatus.pending_legal, MaterialStatus.in_legal_review]),
        )

    priority_order = case(
        (Material.priority == "extreme", 0),
        (Material.priority == "urgent", 1),
        else_=2,
    )
    query = query.order_by(priority_order, Review.created_at.desc())

    results = []
    for review in query.all():
        material = db.query(Material).filter(Material.id == review.material_id).first()
        submitter = db.query(User).filter(User.id == material.submitter_id).first()
        results.append({
            "id": review.id,
            "material_id": material.id,
            "material_name": material.name,
            "submitter_name": submitter.display_name if submitter else "",
            "industry": material.industry,
            "ai_risk_score": review.ai_risk_score,
            "priority": material.priority.value,
            "status": material.status.value,
            "created_at": review.created_at,
            "waiting_hours": round(
                (datetime.now(timezone.utc) - _as_utc(review.created_at)).total_seconds() / 3600,
                1,
            ),
        })
    return results
