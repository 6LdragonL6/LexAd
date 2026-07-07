from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.knowledge import (
    KnowledgeAuditLog,
    KnowledgeImportJob,
    KnowledgeImportJobStatus,
    PlatformRuleSet,
    PlatformRuleStatus,
    PlatformRuleVersion,
    PublicOpinionEvent,
    PublicOpinionEventStatus,
    PublicOpinionEventVersion,
    PublicOpinionLibraryVersion,
)
from app.models.user import User
from app.schemas.admin_knowledge import (
    PublicOpinionImportConfirmRequest,
    PlatformRuleSetCreate,
    PlatformRuleSetUpdate,
    PlatformRuleVersionCreate,
    PublicOpinionEventCreate,
    PublicOpinionEventUpdate,
)
from app.services import model_service


def list_public_opinion_events(
    db: Session,
    status: str | None = None,
    keyword: str | None = None,
) -> tuple[list[PublicOpinionEvent], int]:
    query = db.query(PublicOpinionEvent)
    if status:
        query = query.filter(PublicOpinionEvent.status == PublicOpinionEventStatus(status))
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            (PublicOpinionEvent.title.like(pattern))
            | (PublicOpinionEvent.source_text.like(pattern))
            | (PublicOpinionEvent.consequence_text.like(pattern))
        )
    total = query.count()
    items = query.order_by(PublicOpinionEvent.updated_at.desc()).all()
    return items, total


def create_public_opinion_event(
    db: Session,
    data: PublicOpinionEventCreate,
    actor: User,
) -> PublicOpinionEvent:
    if data.external_id:
        _ensure_external_id_available(db, data.external_id)
    event = PublicOpinionEvent(
        external_id=data.external_id,
        title=data.title,
        source_text=data.source_text,
        consequence_text=data.consequence_text,
        source_meta=data.source_meta,
        status=PublicOpinionEventStatus.draft,
        created_by_id=actor.id,
        updated_by_id=actor.id,
    )
    db.add(event)
    db.flush()
    _audit(db, actor, "public_opinion.create", "public_opinion_event", event.id, after=_event_state(event))
    db.commit()
    db.refresh(event)
    return event


def get_public_opinion_event(db: Session, event_id: str) -> PublicOpinionEvent | None:
    return db.query(PublicOpinionEvent).filter(PublicOpinionEvent.id == event_id).first()


def get_public_opinion_event_versions(db: Session, event_id: str) -> list[PublicOpinionEventVersion]:
    return (
        db.query(PublicOpinionEventVersion)
        .filter(PublicOpinionEventVersion.event_id == event_id)
        .order_by(PublicOpinionEventVersion.version.desc())
        .all()
    )


def update_public_opinion_event(
    db: Session,
    event: PublicOpinionEvent,
    data: PublicOpinionEventUpdate,
    actor: User,
) -> PublicOpinionEvent:
    _require_editable_event(event)
    before = _event_state(event)
    if data.external_id is not None and data.external_id != event.external_id:
        if data.external_id:
            _ensure_external_id_available(db, data.external_id, exclude_event_id=event.id)
        event.external_id = data.external_id
    if data.title is not None:
        event.title = data.title
    if data.source_text is not None:
        event.source_text = data.source_text
    if data.consequence_text is not None:
        event.consequence_text = data.consequence_text
    if data.source_meta is not None:
        event.source_meta = data.source_meta
    event.updated_by_id = actor.id
    _audit(db, actor, "public_opinion.update", "public_opinion_event", event.id, before=before, after=_event_state(event))
    db.commit()
    db.refresh(event)
    return event


def structure_public_opinion_event(
    db: Session,
    event: PublicOpinionEvent,
    actor: User,
) -> PublicOpinionEventVersion:
    _require_editable_event(event)
    if not event.source_text.strip():
        raise ValueError("请先填写事件经过或来源文本")
    before = _event_state(event)
    event.transition_to(PublicOpinionEventStatus.pending_review)
    event.updated_by_id = actor.id
    version_number = _next_event_version(db, event.id)
    structured, model_name, model_version, confidence, edit_notes = _structure_case_with_model_fallback(event)
    version = PublicOpinionEventVersion(
        event_id=event.id,
        version=version_number,
        title=event.title or structured.get("summary") or _summarize_title(event.source_text),
        industry=structured.get("industry", []),
        platforms=structured.get("platforms", []),
        source_text=event.source_text,
        event_process=structured.get("event_process", {}),
        consequences=structured.get("consequences", {}),
        risk_topics=structured.get("risk_topics", []),
        trigger_patterns=structured.get("trigger_patterns", []),
        affected_groups=structured.get("affected_groups", []),
        propagation_drivers=structured.get("propagation_drivers", []),
        normalized_tags=structured.get("normalized_tags", {}),
        severity_level=structured.get("severity_level"),
        summary=structured.get("summary") or _summarize_title(event.source_text),
        confidence=confidence,
        model_name=model_name,
        model_version=model_version,
        generated_at=datetime.now(timezone.utc),
        edited_by_id=actor.id,
        edit_notes=edit_notes,
    )
    db.add(version)
    _audit(
        db,
        actor,
        "public_opinion.structure",
        "public_opinion_event",
        event.id,
        before=before,
        after={**_event_state(event), "version": version_number},
    )
    db.commit()
    db.refresh(version)
    return version


def publish_public_opinion_event(
    db: Session,
    event: PublicOpinionEvent,
    actor: User,
) -> PublicOpinionEvent:
    if event.status not in (PublicOpinionEventStatus.draft, PublicOpinionEventStatus.pending_review):
        raise ValueError("只有草稿或待复核事件可以发布")
    if not (event.title.strip() and event.source_text.strip()):
        raise ValueError("发布前必须填写标题和事件文本")
    before = _event_state(event)
    if not get_public_opinion_event_versions(db, event.id):
        structure_public_opinion_event(db, event, actor)
        event = get_public_opinion_event(db, event.id)
        before = _event_state(event)
    event.status = PublicOpinionEventStatus.published
    event.published_by_id = actor.id
    event.published_at = datetime.now(timezone.utc)
    event.updated_by_id = actor.id
    _create_public_opinion_library_version(db, actor)
    _audit(db, actor, "public_opinion.publish", "public_opinion_event", event.id, before=before, after=_event_state(event))
    db.commit()
    db.refresh(event)
    return event


def archive_public_opinion_event(
    db: Session,
    event: PublicOpinionEvent,
    actor: User,
) -> PublicOpinionEvent:
    if event.status != PublicOpinionEventStatus.published:
        raise ValueError("只有已发布事件可以归档")
    before = _event_state(event)
    event.transition_to(PublicOpinionEventStatus.archived)
    event.archived_by_id = actor.id
    event.archived_at = datetime.now(timezone.utc)
    event.updated_by_id = actor.id
    _create_public_opinion_library_version(db, actor)
    _audit(db, actor, "public_opinion.archive", "public_opinion_event", event.id, before=before, after=_event_state(event))
    db.commit()
    db.refresh(event)
    return event


def restore_public_opinion_event(
    db: Session,
    event: PublicOpinionEvent,
    actor: User,
) -> PublicOpinionEvent:
    if event.status != PublicOpinionEventStatus.archived:
        raise ValueError("只有已归档事件可以恢复")
    before = _event_state(event)
    event.transition_to(PublicOpinionEventStatus.published)
    event.restored_by_id = actor.id
    event.archived_at = None
    event.updated_by_id = actor.id
    _create_public_opinion_library_version(db, actor)
    _audit(db, actor, "public_opinion.restore", "public_opinion_event", event.id, before=before, after=_event_state(event))
    db.commit()
    db.refresh(event)
    return event


def delete_public_opinion_draft(db: Session, event: PublicOpinionEvent, actor: User) -> None:
    if not event.can_delete():
        raise ValueError("已发布或待复核事件不能物理删除，请使用归档")
    before = _event_state(event)
    db.delete(event)
    _audit(db, actor, "public_opinion.delete_draft", "public_opinion_event", event.id, before=before)
    db.commit()


def list_platform_rule_sets(db: Session) -> list[dict[str, Any]]:
    rule_sets = db.query(PlatformRuleSet).order_by(PlatformRuleSet.platform_name.asc()).all()
    results = []
    for rule_set in rule_sets:
        versions = get_platform_rule_versions(db, rule_set.id)
        active = next((version for version in versions if version.status == PlatformRuleStatus.active), None)
        results.append({"rule_set": rule_set, "active_version": active, "versions": versions})
    return results


def create_platform_rule_set(db: Session, data: PlatformRuleSetCreate, actor: User) -> PlatformRuleSet:
    existing = db.query(PlatformRuleSet).filter(PlatformRuleSet.platform_name == data.platform_name).first()
    if existing:
        raise ValueError("平台规则集已存在")
    rule_set = PlatformRuleSet(
        platform_name=data.platform_name,
        display_name=data.display_name,
        description=data.description,
    )
    db.add(rule_set)
    db.flush()
    _audit(db, actor, "platform_rule_set.create", "platform_rule_set", rule_set.id, after=_rule_set_state(rule_set))
    db.commit()
    db.refresh(rule_set)
    return rule_set


def update_platform_rule_set(
    db: Session,
    rule_set: PlatformRuleSet,
    data: PlatformRuleSetUpdate,
    actor: User,
) -> PlatformRuleSet:
    before = _rule_set_state(rule_set)
    if data.display_name is not None:
        rule_set.display_name = data.display_name
    if data.description is not None:
        rule_set.description = data.description
    _audit(db, actor, "platform_rule_set.update", "platform_rule_set", rule_set.id, before=before, after=_rule_set_state(rule_set))
    db.commit()
    db.refresh(rule_set)
    return rule_set


def get_platform_rule_set(db: Session, rule_set_id: str) -> PlatformRuleSet | None:
    return db.query(PlatformRuleSet).filter(PlatformRuleSet.id == rule_set_id).first()


def get_platform_rule_versions(db: Session, rule_set_id: str) -> list[PlatformRuleVersion]:
    return (
        db.query(PlatformRuleVersion)
        .filter(PlatformRuleVersion.rule_set_id == rule_set_id)
        .order_by(PlatformRuleVersion.created_at.desc())
        .all()
    )


def create_platform_rule_version(
    db: Session,
    rule_set: PlatformRuleSet,
    data: PlatformRuleVersionCreate,
    actor: User,
) -> PlatformRuleVersion:
    existing = (
        db.query(PlatformRuleVersion)
        .filter(
            PlatformRuleVersion.rule_set_id == rule_set.id,
            PlatformRuleVersion.version_label == data.version_label,
        )
        .first()
    )
    if existing:
        raise ValueError("该平台下已存在相同版本号")
    previous = _latest_platform_rule_version(db, rule_set.id)
    diff_summary = _diff_rule_items(previous.structured_rules if previous else [], data.structured_rules)
    version = PlatformRuleVersion(
        rule_set_id=rule_set.id,
        version_label=data.version_label,
        source_name=data.source_name,
        source_url=data.source_url,
        published_at=data.published_at,
        effective_at=data.effective_at,
        expires_at=data.expires_at,
        raw_text=data.raw_text,
        structured_rules=data.structured_rules,
        diff_summary=diff_summary,
        status=PlatformRuleStatus.draft,
        imported_by_id=actor.id,
    )
    db.add(version)
    db.flush()
    _audit(db, actor, "platform_rule_version.create", "platform_rule_version", version.id, after=_rule_version_state(version))
    db.commit()
    db.refresh(version)
    return version


def get_platform_rule_version(db: Session, version_id: str) -> PlatformRuleVersion | None:
    return db.query(PlatformRuleVersion).filter(PlatformRuleVersion.id == version_id).first()


def activate_platform_rule_version(db: Session, version: PlatformRuleVersion, actor: User, action: str = "activate") -> PlatformRuleVersion:
    before = _rule_version_state(version)
    active_versions = (
        db.query(PlatformRuleVersion)
        .filter(
            PlatformRuleVersion.rule_set_id == version.rule_set_id,
            PlatformRuleVersion.status == PlatformRuleStatus.active,
            PlatformRuleVersion.id != version.id,
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for active in active_versions:
        active.status = PlatformRuleStatus.expired
        active.expires_at = active.expires_at or now
    version.status = PlatformRuleStatus.active
    version.activated_by_id = actor.id
    version.activated_at = now
    version.effective_at = version.effective_at or now
    version.expires_at = None
    _audit(
        db,
        actor,
        f"platform_rule_version.{action}",
        "platform_rule_version",
        version.id,
        before=before,
        after=_rule_version_state(version),
    )
    db.commit()
    db.refresh(version)
    return version


def list_import_jobs(db: Session) -> list[KnowledgeImportJob]:
    return db.query(KnowledgeImportJob).order_by(KnowledgeImportJob.created_at.desc()).all()


def get_import_job(db: Session, job_id: str) -> KnowledgeImportJob | None:
    return db.query(KnowledgeImportJob).filter(KnowledgeImportJob.id == job_id).first()


def preview_public_opinion_import(
    db: Session,
    payload: dict[str, Any],
    file_name: str,
    actor: User,
) -> KnowledgeImportJob:
    validation = _validate_public_opinion_import_payload(db, payload)
    status = (
        KnowledgeImportJobStatus.validated
        if validation["invalid_items"] == 0
        else KnowledgeImportJobStatus.validation_failed
    )
    job = KnowledgeImportJob(
        import_type="public_opinion",
        file_name=file_name,
        status=status,
        total_items=validation["total_items"],
        valid_items=validation["valid_items"],
        invalid_items=validation["invalid_items"],
        error_summary={
            "schema_errors": validation["schema_errors"],
            "item_errors": validation["item_errors"],
            "duplicate_external_ids": validation["duplicate_external_ids"],
        },
        options={"valid_events": validation["valid_events"]},
        created_by_id=actor.id,
    )
    db.add(job)
    db.flush()
    _audit(db, actor, "public_opinion_import.preview", "knowledge_import_job", job.id, after=_import_job_state(job))
    db.commit()
    db.refresh(job)
    return job


def confirm_public_opinion_import(
    db: Session,
    job: KnowledgeImportJob,
    data: PublicOpinionImportConfirmRequest,
    actor: User,
) -> dict[str, Any]:
    if job.import_type != "public_opinion":
        raise ValueError("导入任务类型不匹配")
    if job.status not in (KnowledgeImportJobStatus.validated, KnowledgeImportJobStatus.validation_failed):
        raise ValueError("只有完成预检的导入任务可以确认导入")
    valid_events = job.options.get("valid_events", []) if isinstance(job.options, dict) else []
    if not valid_events:
        raise ValueError("没有可导入的合格事件")

    before = _import_job_state(job)
    created_event_ids: list[str] = []
    updated_event_ids: list[str] = []
    skipped_external_ids: list[str] = []
    job.status = KnowledgeImportJobStatus.importing
    db.flush()

    for item in valid_events:
        external_id = item.get("external_id")
        existing = (
            db.query(PublicOpinionEvent)
            .filter(PublicOpinionEvent.external_id == external_id)
            .first()
            if external_id
            else None
        )
        if existing:
            action = data.duplicate_actions.get(external_id, "skip")
            if action == "skip":
                skipped_external_ids.append(external_id)
                continue
            if action == "update":
                if existing.status in (PublicOpinionEventStatus.published, PublicOpinionEventStatus.archived):
                    skipped_external_ids.append(external_id)
                    continue
                existing.title = item["title"]
                existing.source_text = item["source_text"]
                existing.consequence_text = item["consequence_text"]
                existing.source_meta = item["source_meta"]
                existing.updated_by_id = actor.id
                updated_event_ids.append(existing.id)
                if data.run_structure:
                    structure_public_opinion_event(db, existing, actor)
                continue
            if action != "create":
                raise ValueError(f"不支持的重复处理方式：{action}")

        event = PublicOpinionEvent(
            external_id=None if existing else external_id,
            title=item["title"],
            source_text=item["source_text"],
            consequence_text=item["consequence_text"],
            source_meta=item["source_meta"],
            status=PublicOpinionEventStatus.draft,
            created_by_id=actor.id,
            updated_by_id=actor.id,
        )
        db.add(event)
        db.flush()
        created_event_ids.append(event.id)
        if data.run_structure:
            structure_public_opinion_event(db, event, actor)

    job.status = KnowledgeImportJobStatus.completed
    job.completed_at = datetime.now(timezone.utc)
    job.options = {
        **(job.options or {}),
        "created_event_ids": created_event_ids,
        "updated_event_ids": updated_event_ids,
        "skipped_external_ids": skipped_external_ids,
    }
    _audit(
        db,
        actor,
        "public_opinion_import.confirm",
        "knowledge_import_job",
        job.id,
        before=before,
        after=_import_job_state(job),
    )
    db.commit()
    db.refresh(job)
    return {
        "job": job,
        "created_event_ids": created_event_ids,
        "updated_event_ids": updated_event_ids,
        "skipped_external_ids": skipped_external_ids,
    }


def list_audit_logs(db: Session, target_type: str | None = None) -> list[KnowledgeAuditLog]:
    query = db.query(KnowledgeAuditLog)
    if target_type:
        query = query.filter(KnowledgeAuditLog.target_type == target_type)
    return query.order_by(KnowledgeAuditLog.created_at.desc()).all()


def public_opinion_import_template() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "events": [
            {
                "external_id": "case-001",
                "title": "事件标题",
                "industry": ["食品"],
                "platforms": ["微博", "抖音"],
                "occurred_at": "2026-01-15",
                "source_text": "相关报道、评论摘要或完整事实材料",
                "sources": [
                    {
                        "name": "来源名称",
                        "url": "https://example.com/article",
                        "published_at": "2026-01-16",
                    }
                ],
                "event_process": {
                    "trigger": "争议由什么内容或表达触发",
                    "timeline": [
                        {
                            "at": "2026-01-15",
                            "stage": "发生",
                            "description": "事件经过",
                        }
                    ],
                    "brand_response": "企业采取的回应",
                    "outcome": "事件最终结果",
                },
                "consequences": {
                    "reputation": "品牌声誉影响",
                    "business": "销量、合作或市值等影响",
                    "regulatory": "约谈、处罚或整改情况",
                    "duration_days": 14,
                    "severity_hint": "high",
                },
                "notes": "其他补充信息",
            }
        ],
    }


def _ensure_external_id_available(db: Session, external_id: str, exclude_event_id: str | None = None) -> None:
    query = db.query(PublicOpinionEvent).filter(PublicOpinionEvent.external_id == external_id)
    if exclude_event_id:
        query = query.filter(PublicOpinionEvent.id != exclude_event_id)
    if query.first():
        raise ValueError("external_id 已存在，请选择更新或跳过该事件")


def _require_editable_event(event: PublicOpinionEvent) -> None:
    if event.status in (PublicOpinionEventStatus.published, PublicOpinionEventStatus.archived):
        raise ValueError("已发布或已归档事件不能直接编辑")


def _next_event_version(db: Session, event_id: str) -> int:
    latest = db.query(func.max(PublicOpinionEventVersion.version)).filter(PublicOpinionEventVersion.event_id == event_id).scalar()
    return int(latest or 0) + 1


def _create_public_opinion_library_version(db: Session, actor: User) -> PublicOpinionLibraryVersion:
    published_ids = [
        row[0]
        for row in (
            db.query(PublicOpinionEvent.id)
            .filter(PublicOpinionEvent.status == PublicOpinionEventStatus.published)
            .order_by(PublicOpinionEvent.updated_at.asc())
            .all()
        )
    ]
    latest = db.query(func.max(PublicOpinionLibraryVersion.version)).scalar()
    library_version = PublicOpinionLibraryVersion(
        version=int(latest or 0) + 1,
        event_ids=published_ids,
        event_count=len(published_ids),
        notes="资料库由管理员发布/归档/恢复事件后自动生成快照",
        created_by_id=actor.id,
    )
    db.add(library_version)
    db.flush()
    return library_version


def _latest_platform_rule_version(db: Session, rule_set_id: str) -> PlatformRuleVersion | None:
    return (
        db.query(PlatformRuleVersion)
        .filter(PlatformRuleVersion.rule_set_id == rule_set_id)
        .order_by(PlatformRuleVersion.created_at.desc())
        .first()
    )


def _diff_rule_items(old_rules: list[dict[str, Any]], new_rules: list[dict[str, Any]]) -> dict[str, Any]:
    old_map = {_rule_key(rule, index): rule for index, rule in enumerate(old_rules)}
    new_map = {_rule_key(rule, index): rule for index, rule in enumerate(new_rules)}
    added = [key for key in new_map.keys() if key not in old_map]
    removed = [key for key in old_map.keys() if key not in new_map]
    changed = [key for key in new_map.keys() if key in old_map and new_map[key] != old_map[key]]
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
    }


def _rule_key(rule: dict[str, Any], index: int) -> str:
    return str(rule.get("rule_id") or rule.get("id") or rule.get("title") or f"index:{index}")


def _summarize_title(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:60] if compact else "未命名舆情事件"


def _structure_case_with_model_fallback(event: PublicOpinionEvent) -> tuple[dict[str, Any], str, str, int, str]:
    try:
        structured = model_service.structure_public_opinion_case(
            title=event.title,
            source_text=event.source_text,
            consequence_text=event.consequence_text,
        )
        confidence = structured.get("confidence")
        return (
            structured,
            "deepseek",
            "shared-model-service",
            confidence if isinstance(confidence, int) else 0,
            "由统一模型服务整理，管理员仍需人工复核。",
        )
    except model_service.ModelServiceError as exc:
        return (
            _deterministic_public_opinion_structure(event),
            "deterministic-fallback",
            "v0.4.2-stage3",
            0,
            f"模型整理暂不可用，已使用规则降级整理：{str(exc)[:160]}",
        )


def _deterministic_public_opinion_structure(event: PublicOpinionEvent) -> dict[str, Any]:
    return {
        "industry": [],
        "platforms": [],
        "event_process": {
            "trigger": "",
            "timeline": [],
            "brand_response": "",
            "outcome": event.consequence_text,
        },
        "consequences": {
            "reputation": event.consequence_text,
            "business": "",
            "regulatory": "",
            "duration_days": None,
            "severity_hint": None,
        },
        "risk_topics": [],
        "trigger_patterns": [],
        "affected_groups": [],
        "propagation_drivers": [],
        "normalized_tags": {},
        "severity_level": None,
        "summary": _summarize_title(event.source_text),
        "confidence": 0,
    }


def _validate_public_opinion_import_payload(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    schema_errors: list[str] = []
    item_errors: list[dict[str, Any]] = []
    duplicate_external_ids: list[str] = []
    valid_events: list[dict[str, Any]] = []

    if payload.get("schema_version") != "1.0":
        schema_errors.append("schema_version 必须为 1.0")
    events = payload.get("events")
    if not isinstance(events, list):
        schema_errors.append("events 必须是事件数组")
        events = []

    seen_external_ids: set[str] = set()
    for index, event in enumerate(events):
        errors = _validate_public_opinion_import_event(event)
        external_id = event.get("external_id") if isinstance(event, dict) else None
        if external_id:
            if external_id in seen_external_ids:
                errors.append("同一文件中 external_id 重复")
            seen_external_ids.add(external_id)
            if db.query(PublicOpinionEvent).filter(PublicOpinionEvent.external_id == external_id).first():
                duplicate_external_ids.append(external_id)
        if errors:
            item_errors.append({"index": index, "external_id": external_id, "errors": errors})
            continue
        valid_events.append(_normalize_import_event(event))

    return {
        "total_items": len(events),
        "valid_items": len(valid_events),
        "invalid_items": len(item_errors) + len(schema_errors),
        "schema_errors": schema_errors,
        "item_errors": item_errors,
        "duplicate_external_ids": duplicate_external_ids,
        "valid_events": valid_events,
    }


def _validate_public_opinion_import_event(event: Any) -> list[str]:
    if not isinstance(event, dict):
        return ["事件必须是对象"]
    errors = []
    if not str(event.get("title") or "").strip():
        errors.append("缺少标题 title")
    if not str(event.get("source_text") or "").strip():
        errors.append("缺少事件材料 source_text")
    event_process = event.get("event_process")
    if not isinstance(event_process, dict):
        errors.append("缺少事件过程 event_process")
    else:
        if not str(event_process.get("trigger") or "").strip():
            errors.append("缺少触发原因 event_process.trigger")
        if not str(event_process.get("outcome") or "").strip():
            errors.append("缺少事件结果 event_process.outcome")
    return errors


def _normalize_import_event(event: dict[str, Any]) -> dict[str, Any]:
    event_process = event.get("event_process") or {}
    consequences = event.get("consequences") or {}
    consequence_text = (
        event_process.get("outcome")
        or consequences.get("reputation")
        or consequences.get("business")
        or consequences.get("regulatory")
        or ""
    )
    return {
        "external_id": event.get("external_id"),
        "title": event.get("title", ""),
        "source_text": event.get("source_text", ""),
        "consequence_text": consequence_text,
        "source_meta": {
            "industry": event.get("industry", []),
            "platforms": event.get("platforms", []),
            "occurred_at": event.get("occurred_at"),
            "sources": event.get("sources", []),
            "event_process": event_process,
            "consequences": consequences,
            "notes": event.get("notes", ""),
            "raw_import_event": event,
        },
    }


def _event_state(event: PublicOpinionEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "external_id": event.external_id,
        "title": event.title,
        "status": event.status.value if hasattr(event.status, "value") else event.status,
    }


def _rule_set_state(rule_set: PlatformRuleSet) -> dict[str, Any]:
    return {
        "id": rule_set.id,
        "platform_name": rule_set.platform_name,
        "display_name": rule_set.display_name,
    }


def _rule_version_state(version: PlatformRuleVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "rule_set_id": version.rule_set_id,
        "version_label": version.version_label,
        "status": version.status.value if hasattr(version.status, "value") else version.status,
    }


def _import_job_state(job: KnowledgeImportJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "import_type": job.import_type,
        "status": job.status.value if hasattr(job.status, "value") else job.status,
        "total_items": job.total_items,
        "valid_items": job.valid_items,
        "invalid_items": job.invalid_items,
    }


def _audit(
    db: Session,
    actor: User,
    action: str,
    target_type: str,
    target_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    db.add(
        KnowledgeAuditLog(
            actor_id=actor.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_state=before or {},
            after_state=after or {},
        )
    )
