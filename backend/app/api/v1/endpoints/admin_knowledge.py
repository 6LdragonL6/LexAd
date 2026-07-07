from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_knowledge import (
    KnowledgeAuditLogOut,
    KnowledgeImportJobOut,
    KnowledgeImportConfirmResult,
    PlatformRuleSetCreate,
    PlatformRuleSetDetail,
    PlatformRuleSetList,
    PlatformRuleSetOut,
    PlatformRuleSetUpdate,
    PlatformRuleVersionCreate,
    PlatformRuleVersionOut,
    PublicOpinionEventCreate,
    PublicOpinionEventDetail,
    PublicOpinionEventList,
    PublicOpinionEventOut,
    PublicOpinionEventUpdate,
    PublicOpinionEventVersionOut,
    PublicOpinionImportConfirmRequest,
    PublicOpinionImportPreviewRequest,
)
from app.services import admin_knowledge_service as service


router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/public-opinion/events", response_model=PublicOpinionEventList)
def list_public_opinion_events(
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        items, total = service.list_public_opinion_events(db, status=status_filter, keyword=keyword)
        return PublicOpinionEventList(items=items, total=total)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/public-opinion/events", response_model=PublicOpinionEventOut, status_code=status.HTTP_201_CREATED)
def create_public_opinion_event(
    body: PublicOpinionEventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    try:
        return service.create_public_opinion_event(db, body, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/public-opinion/events/{event_id}", response_model=PublicOpinionEventDetail)
def get_public_opinion_event(event_id: str, db: Session = Depends(get_db)):
    event = _get_event_or_404(db, event_id)
    versions = service.get_public_opinion_event_versions(db, event_id)
    return PublicOpinionEventDetail(event=event, versions=versions)


@router.put("/public-opinion/events/{event_id}", response_model=PublicOpinionEventOut)
def update_public_opinion_event(
    event_id: str,
    body: PublicOpinionEventUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    event = _get_event_or_404(db, event_id)
    try:
        return service.update_public_opinion_event(db, event, body, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/public-opinion/events/{event_id}/structure", response_model=PublicOpinionEventVersionOut, status_code=202)
def structure_public_opinion_event(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    event = _get_event_or_404(db, event_id)
    try:
        return service.structure_public_opinion_event(db, event, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/public-opinion/events/{event_id}/publish", response_model=PublicOpinionEventOut)
def publish_public_opinion_event(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    event = _get_event_or_404(db, event_id)
    try:
        return service.publish_public_opinion_event(db, event, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/public-opinion/events/{event_id}/archive", response_model=PublicOpinionEventOut)
def archive_public_opinion_event(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    event = _get_event_or_404(db, event_id)
    try:
        return service.archive_public_opinion_event(db, event, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/public-opinion/events/{event_id}/restore", response_model=PublicOpinionEventOut)
def restore_public_opinion_event(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    event = _get_event_or_404(db, event_id)
    try:
        return service.restore_public_opinion_event(db, event, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/public-opinion/events/{event_id}", status_code=204)
def delete_public_opinion_draft(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    event = _get_event_or_404(db, event_id)
    try:
        service.delete_public_opinion_draft(db, event, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return None


@router.get("/public-opinion/import-template")
def get_public_opinion_import_template():
    return service.public_opinion_import_template()


@router.post("/public-opinion/import/preview", response_model=KnowledgeImportJobOut, status_code=status.HTTP_201_CREATED)
def preview_public_opinion_import(
    body: PublicOpinionImportPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    return service.preview_public_opinion_import(db, body.payload, body.file_name, user)


@router.post("/public-opinion/imports/{job_id}/confirm", response_model=KnowledgeImportConfirmResult)
def confirm_public_opinion_import(
    job_id: str,
    body: PublicOpinionImportConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    job = service.get_import_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    try:
        return service.confirm_public_opinion_import(db, job, body, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/platform-rules", response_model=PlatformRuleSetList)
def list_platform_rule_sets(db: Session = Depends(get_db)):
    items = [PlatformRuleSetDetail(**item) for item in service.list_platform_rule_sets(db)]
    return PlatformRuleSetList(items=items, total=len(items))


@router.post("/platform-rules", response_model=PlatformRuleSetOut, status_code=status.HTTP_201_CREATED)
def create_platform_rule_set(
    body: PlatformRuleSetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    try:
        return service.create_platform_rule_set(db, body, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/platform-rules/{rule_set_id}", response_model=PlatformRuleSetDetail)
def get_platform_rule_set(rule_set_id: str, db: Session = Depends(get_db)):
    rule_set = _get_rule_set_or_404(db, rule_set_id)
    versions = service.get_platform_rule_versions(db, rule_set.id)
    active = next((version for version in versions if getattr(version.status, "value", version.status) == "active"), None)
    return PlatformRuleSetDetail(rule_set=rule_set, active_version=active, versions=versions)


@router.put("/platform-rules/{rule_set_id}", response_model=PlatformRuleSetOut)
def update_platform_rule_set(
    rule_set_id: str,
    body: PlatformRuleSetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    rule_set = _get_rule_set_or_404(db, rule_set_id)
    return service.update_platform_rule_set(db, rule_set, body, user)


@router.post("/platform-rules/{rule_set_id}/versions", response_model=PlatformRuleVersionOut, status_code=status.HTTP_201_CREATED)
def create_platform_rule_version(
    rule_set_id: str,
    body: PlatformRuleVersionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    rule_set = _get_rule_set_or_404(db, rule_set_id)
    try:
        return service.create_platform_rule_version(db, rule_set, body, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/platform-rule-versions/{version_id}", response_model=PlatformRuleVersionOut)
def get_platform_rule_version(version_id: str, db: Session = Depends(get_db)):
    return _get_rule_version_or_404(db, version_id)


@router.get("/platform-rule-versions/{version_id}/diff")
def get_platform_rule_version_diff(version_id: str, db: Session = Depends(get_db)):
    version = _get_rule_version_or_404(db, version_id)
    return version.diff_summary


@router.post("/platform-rule-versions/{version_id}/activate", response_model=PlatformRuleVersionOut)
def activate_platform_rule_version(
    version_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    version = _get_rule_version_or_404(db, version_id)
    return service.activate_platform_rule_version(db, version, user, action="activate")


@router.post("/platform-rule-versions/{version_id}/rollback", response_model=PlatformRuleVersionOut)
def rollback_platform_rule_version(
    version_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    version = _get_rule_version_or_404(db, version_id)
    return service.activate_platform_rule_version(db, version, user, action="rollback")


@router.get("/imports", response_model=list[KnowledgeImportJobOut])
def list_import_jobs(db: Session = Depends(get_db)):
    return service.list_import_jobs(db)


@router.get("/audit-logs", response_model=list[KnowledgeAuditLogOut])
def list_audit_logs(target_type: str | None = None, db: Session = Depends(get_db)):
    return service.list_audit_logs(db, target_type=target_type)


def _get_event_or_404(db: Session, event_id: str):
    event = service.get_public_opinion_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="舆情事件不存在")
    return event


def _get_rule_set_or_404(db: Session, rule_set_id: str):
    rule_set = service.get_platform_rule_set(db, rule_set_id)
    if not rule_set:
        raise HTTPException(status_code=404, detail="平台规则集不存在")
    return rule_set


def _get_rule_version_or_404(db: Session, version_id: str):
    version = service.get_platform_rule_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="平台规则版本不存在")
    return version
