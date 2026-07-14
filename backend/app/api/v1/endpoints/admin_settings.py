from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AiConfigStatus,
    AiConfigTestResult,
    ApiKeyUpdate,
    DeleteTargetRequest,
    RecycleBinEntryOut,
    RecycleBinList,
)
from app.services import admin_settings_service, deepseek_gateway, recycle_bin_service


router = APIRouter()


@router.get("/ai", response_model=AiConfigStatus)
def get_ai_config(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return admin_settings_service.get_ai_config_status(db)


@router.put("/ai", response_model=AiConfigStatus)
def update_ai_config(
    body: ApiKeyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    try:
        admin_settings_service.save_api_key(db, body.api_key, user)
        return admin_settings_service.get_ai_config_status(db)
    except admin_settings_service.SecureSettingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except deepseek_gateway.DeepSeekGatewayError as exc:
        code = 400 if exc.category in {"authentication", "bad_request"} else 502
        raise HTTPException(status_code=code, detail=str(exc))


@router.post("/ai/test", response_model=AiConfigTestResult)
def test_ai_config(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        deepseek_gateway.validate_api_key(admin_settings_service.get_api_key(db))
        return AiConfigTestResult(ok=True, message="DeepSeek 配置可用", tested_at=datetime.now(timezone.utc))
    except (admin_settings_service.SecureSettingError, deepseek_gateway.DeepSeekGatewayError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.delete("/ai", status_code=status.HTTP_204_NO_CONTENT)
def clear_ai_config(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    admin_settings_service.clear_api_key(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/recycle-bin", response_model=RecycleBinList)
def get_recycle_bin(
    target_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        items, total = recycle_bin_service.list_entries(
            db, target_type=target_type, page=page, page_size=page_size
        )
        return RecycleBinList(items=[RecycleBinEntryOut(**item) for item in items], total=total, page=page, page_size=page_size)
    except recycle_bin_service.RecycleBinError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/recycle-bin", response_model=RecycleBinEntryOut, status_code=201)
def delete_target(
    body: DeleteTargetRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    try:
        entry = recycle_bin_service.move_to_recycle_bin(db, body.target_type, body.target_id, user)
        items, _ = recycle_bin_service.list_entries(db, target_type=body.target_type, page=1, page_size=100)
        item = next(value for value in items if value["id"] == entry.id)
        return RecycleBinEntryOut(**item)
    except recycle_bin_service.RecycleBinError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/recycle-bin/{entry_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
def restore_target(
    entry_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    try:
        recycle_bin_service.restore_entry(db, entry_id, user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except recycle_bin_service.RecycleBinError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/recycle-bin/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def purge_target(
    entry_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    try:
        recycle_bin_service.purge_entry(db, entry_id, user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except recycle_bin_service.RecycleBinError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
