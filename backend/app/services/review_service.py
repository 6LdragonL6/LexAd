from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.engine.pipeline import run_review_pipeline
from app.engine.public_opinion import run_public_opinion_review
from app.models.knowledge import ReviewModuleStatus
from app.models.material import Material, MaterialStatus, MaterialSubmissionSnapshot
from app.models.review import LegalDecision, Review
from app.models.user import User, UserRole
from app.schemas.review import LegalDecisionRequest


def create_ai_review(db: Session, material_id: str) -> tuple[Review, bool]:
    material = db.query(Material).filter(Material.id == material_id, Material.deleted_at.is_(None)).first()
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
        running.error_message = "上一轮审查任务因服务中断未完成，请重新审查"
        running.completed_at = datetime.now(timezone.utc)
        material.status = MaterialStatus.draft
        db.commit()

    if material.status not in (MaterialStatus.draft, MaterialStatus.returned):
        raise ValueError("当前物料状态不允许重新发起 AI 审查")
    if not material.display_name:
        material.display_name = material.name

    snapshot = (
        db.query(MaterialSubmissionSnapshot)
        .filter(
            MaterialSubmissionSnapshot.material_id == material.id,
            MaterialSubmissionSnapshot.version == material.current_version,
        )
        .first()
    )
    if snapshot is None:
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

    material.status = MaterialStatus.ai_reviewing
    review = Review(
        material_id=material_id,
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
    db.commit()
    db.refresh(review)
    return review, True


def recover_interrupted_reviews() -> int:
    """Mark abandoned in-process reviews retryable when the application starts."""
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
        reviews = db.query(Review).filter(Review.task_status == "processing").all()
        recovered = 0
        for review in reviews:
            if _as_utc(review.created_at) > cutoff:
                continue
            review.task_status = "failed"
            review.error_message = "审查任务因服务重启中断，请重新审查"
            review.completed_at = datetime.now(timezone.utc)
            material = db.query(Material).filter(
                Material.id == review.material_id, Material.deleted_at.is_(None)
            ).first()
            if material and material.status == MaterialStatus.ai_reviewing:
                material.status = MaterialStatus.draft
            recovered += 1
        if recovered:
            db.commit()
        return recovered
    finally:
        db.close()


def execute_ai_review(review_id: str) -> None:
    """Execute legal/platform and public-opinion branches in an independent DB session."""
    db = SessionLocal()
    try:
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review or review.task_status != "processing":
            return
        material = db.query(Material).filter(Material.id == review.material_id, Material.deleted_at.is_(None)).first()
        if not material:
            raise ValueError("物料不存在")

        review.started_at = datetime.now(timezone.utc)
        db.commit()

        legal_succeeded = _execute_legal_branch(db, review.id, material.id)
        public_opinion_succeeded = _execute_public_opinion_branch(db, review.id, material.id)

        review = db.query(Review).filter(Review.id == review_id).first()
        if not review or review.task_status != "processing":
            return
        material = db.query(Material).filter(
            Material.id == review.material_id, Material.deleted_at.is_(None)
        ).first()
        if material is None:
            return
        review.completed_at = datetime.now(timezone.utc)
        if legal_succeeded:
            review.task_status = "completed"
            review.error_message = None
            material.status = MaterialStatus.pending_legal
        else:
            review.task_status = "failed"
            review.error_message = review.legal_module_error or review.public_opinion_module_error
            if material.status == MaterialStatus.ai_reviewing:
                material.status = MaterialStatus.draft
        db.commit()
    except Exception as exc:
        db.rollback()
        review = db.query(Review).filter(Review.id == review_id).first()
        if review:
            material = db.query(Material).filter(
                Material.id == review.material_id, Material.deleted_at.is_(None)
            ).first()
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


def _execute_legal_branch(db: Session, review_id: str, material_id: str) -> bool:
    review = db.query(Review).filter(Review.id == review_id).first()
    material = db.query(Material).filter(Material.id == material_id, Material.deleted_at.is_(None)).first()
    if not review or review.task_status != "processing" or material is None:
        return False
    snapshot = db.get(MaterialSubmissionSnapshot, review.submission_snapshot_id) if review.submission_snapshot_id else None
    if snapshot is None:
        review.legal_module_status = ReviewModuleStatus.failed
        review.legal_module_error = "本次审核缺少提交快照，无法安全执行法律审查"
        review.legal_module_completed_at = datetime.now(timezone.utc)
        db.commit()
        return False
    review.legal_module_status = ReviewModuleStatus.running
    db.commit()
    try:
        engine_result = run_review_pipeline(
            snapshot.raw_text,
            snapshot.industry,
            snapshot.platforms,
            db,
        )
        review = db.query(Review).filter(Review.id == review_id).first()
        material = db.query(Material).filter(
            Material.id == material_id, Material.deleted_at.is_(None)
        ).first()
        if not review or review.task_status != "processing" or material is None:
            return False
        review.legal_compliance_score = engine_result.compliance_score
        review.ai_result = engine_result.model_dump()
        review.platform_rule_version_ids = engine_result.platform_rule_version_ids
        review.legal_module_status = ReviewModuleStatus.succeeded
        review.legal_module_error = None
        review.legal_module_completed_at = datetime.now(timezone.utc)
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review or review.task_status != "processing":
            return False
        review.legal_module_status = ReviewModuleStatus.failed
        review.legal_module_error = _safe_error_message(exc)
        review.legal_module_completed_at = datetime.now(timezone.utc)
        db.commit()
        return False


def _execute_public_opinion_branch(db: Session, review_id: str, material_id: str) -> bool:
    review = db.query(Review).filter(Review.id == review_id).first()
    material = db.query(Material).filter(Material.id == material_id, Material.deleted_at.is_(None)).first()
    if not review or review.task_status != "processing" or material is None:
        return False
    snapshot = db.get(MaterialSubmissionSnapshot, review.submission_snapshot_id) if review.submission_snapshot_id else None
    if snapshot is None:
        review.public_opinion_module_status = ReviewModuleStatus.failed
        review.public_opinion_module_error = "本次审核缺少提交快照，无法安全执行舆情审查"
        review.public_opinion_module_completed_at = datetime.now(timezone.utc)
        db.commit()
        return False
    review.public_opinion_module_status = ReviewModuleStatus.running
    db.commit()
    try:
        public_opinion = run_public_opinion_review(
            material_text=snapshot.raw_text,
            industry=snapshot.industry,
            platforms=snapshot.platforms,
            db=db,
        )
        review = db.query(Review).filter(Review.id == review_id).first()
        material = db.query(Material).filter(
            Material.id == material_id, Material.deleted_at.is_(None)
        ).first()
        if not review or review.task_status != "processing" or material is None:
            return False
        review.public_opinion_result = public_opinion.result
        review.public_opinion_safety_score = public_opinion.safety_score
        review.public_opinion_library_version_id = public_opinion.library_version_id
        if public_opinion.status == "unavailable":
            review.public_opinion_module_status = ReviewModuleStatus.unavailable
            review.public_opinion_module_error = public_opinion.error or public_opinion.result.get("message")
            succeeded = False
        else:
            review.public_opinion_module_status = ReviewModuleStatus.succeeded
            review.public_opinion_module_error = None
            succeeded = True
        review.public_opinion_module_completed_at = datetime.now(timezone.utc)
        db.commit()
        return succeeded
    except Exception as exc:
        db.rollback()
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review or review.task_status != "processing":
            return False
        review.public_opinion_module_status = ReviewModuleStatus.failed
        review.public_opinion_module_error = _safe_error_message(exc)
        review.public_opinion_module_completed_at = datetime.now(timezone.utc)
        db.commit()
        return False


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
    if review.task_status != "completed" or review.legal_module_status != ReviewModuleStatus.succeeded:
        raise ValueError("法律合规审查尚未完成")
    if review.legal_decision is not None:
        raise ValueError("该审查已经提交法务决定，不能重复覆盖")
    public_opinion_status = review.public_opinion_module_status
    public_opinion_result = review.public_opinion_result or {}
    if public_opinion_status in (ReviewModuleStatus.pending, ReviewModuleStatus.running):
        raise ValueError("舆情审查仍在处理中，暂不能提交法务决定")
    requires_public_opinion_manual_review = (
        public_opinion_status in (None, ReviewModuleStatus.failed, ReviewModuleStatus.unavailable)
        or not public_opinion_result
        or public_opinion_result.get("status") == "manual_review"
        or bool(public_opinion_result.get("requires_manual_review"))
    )
    if requires_public_opinion_manual_review:
        if not data.public_opinion_manually_reviewed:
            raise ValueError("舆情审查不可用，请完成人工舆情复核并确认")

    material = db.query(Material).filter(Material.id == review.material_id, Material.deleted_at.is_(None)).first()
    if material is None:
        raise ValueError("物料不存在")
    review.legal_decision = LegalDecision(data.decision)
    review.legal_notes = data.notes
    review.return_reasons = data.return_reasons
    review.reviewer_id = reviewer.id
    review.reviewed_at = datetime.now(timezone.utc)

    if data.decision == "approved":
        material.status = MaterialStatus.approved
    elif data.decision == "conditional":
        material.status = MaterialStatus.conditional_approved
    elif data.decision == "returned":
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
    query = query.filter(Review.created_at == latest_review_created_at, Material.deleted_at.is_(None))

    if user.role == UserRole.marketing:
        query = query.filter(Material.submitter_id == user.id)
    else:
        query = query.filter(
            Review.task_status == "completed",
            Review.legal_module_status == ReviewModuleStatus.succeeded,
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
        material = db.query(Material).filter(
            Material.id == review.material_id, Material.deleted_at.is_(None)
        ).first()
        if material is None:
            continue
        snapshot = review.submission or (
            db.get(MaterialSubmissionSnapshot, review.submission_snapshot_id)
            if review.submission_snapshot_id else None
        )
        submitter = db.query(User).filter(User.id == material.submitter_id).first()
        results.append(
            {
                "id": review.id,
                "material_id": material.id,
                "material_name": material.display_name or material.name,
                "submitter_name": submitter.display_name if submitter else "",
                "industry": snapshot.industry if snapshot else material.industry,
                "legal_compliance_score": review.legal_compliance_score,
                "public_opinion_safety_score": review.public_opinion_safety_score,
                "priority": snapshot.priority if snapshot else material.priority.value,
                "status": material.status.value,
                "created_at": review.created_at,
                "waiting_hours": round(
                    (datetime.now(timezone.utc) - _as_utc(review.created_at)).total_seconds() / 3600,
                    1,
                ),
                "legal_decision": review.legal_decision.value if review.legal_decision else None,
                "return_reasons": review.return_reasons,
                "legal_notes": review.legal_notes,
                "version": review.version,
                "material_version": material.current_version,
            }
        )
    return results
