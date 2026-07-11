import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import ensure_material_visible, get_current_user, require_marketing
from app.models.material import Material, MaterialStatus
from app.models.brand import Brand, BrandStatus
from app.models.review import Review
from app.models.user import User
from app.schemas.material import MaterialSubmit, MaterialUpdate, MaterialOut, MaterialListItem, PreviewTextResponse
from app.services import material_service
from app.services.file_extraction import FileExtractionService, ExtractionError
from app.storage import save_upload_temp, cleanup_temp
from app.core.config import get_settings

router = APIRouter()
_extraction_svc = FileExtractionService()
_settings = get_settings()

SUPPORTED_FORMATS = "JPG/PNG/GIF/BMP/PDF/DOCX/PPTX/XLSX/TXT"
MAX_UPLOAD_BYTES = _settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_EXTRACTED_TEXT_LENGTH = 50_000


@router.post("/submit", response_model=MaterialOut, status_code=201)
async def submit_material(
    body: str = Form(...),
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_marketing),
):
    data = MaterialSubmit(**json.loads(body))
    extracted_text = ""

    if data.brand_id:
        brand = db.query(Brand).filter(Brand.id == data.brand_id, Brand.status == BrandStatus.active).first()
        if not brand:
            raise HTTPException(status_code=422, detail="引用的品牌不存在或已归档")

    if file and file.filename:
        _validate_file(file)
        tmp_path = None
        try:
            mime = _extraction_svc.mime_from_extension(file.filename)
            if not _extraction_svc.is_supported(mime):
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件格式，支持：{SUPPORTED_FORMATS}",
                )
            tmp_path = save_upload_temp(file)
            result = await asyncio.to_thread(_extraction_svc.extract, tmp_path, mime)
            _ensure_text_within_limit(result.text)
            extracted_text = result.text
        except ExtractionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            if tmp_path:
                cleanup_temp(tmp_path)

    if not extracted_text.strip() and not data.raw_text.strip():
        raise HTTPException(
            status_code=400,
            detail="请提供广告文案内容或上传文件",
        )

    material = material_service.create_material(db, data, user.id, extracted_text, brand_id=data.brand_id)
    return material


@router.post("/preview-text", response_model=PreviewTextResponse)
async def preview_text(
    file: UploadFile = File(...),
    user: User = Depends(require_marketing),
):
    _validate_file(file)
    mime = _extraction_svc.mime_from_extension(file.filename)
    if not _extraction_svc.is_supported(mime):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，支持：{SUPPORTED_FORMATS}",
        )

    tmp_path = None
    try:
        tmp_path = save_upload_temp(file)
        result = await asyncio.to_thread(_extraction_svc.extract, tmp_path, mime)
        _ensure_text_within_limit(result.text)
        return PreviewTextResponse(
            text=result.text,
            quality=result.quality,
            source_format=result.source_format,
        )
    except ExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if tmp_path:
            cleanup_temp(tmp_path)


def _validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大（上限 {_settings.MAX_UPLOAD_SIZE_MB}MB），请压缩后重试",
        )


def _ensure_text_within_limit(text: str) -> None:
    if len(text) > MAX_EXTRACTED_TEXT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail="提取文本过长（上限 50000 字符），请拆分文件或精简内容后重试",
        )


@router.get("/list", response_model=list[MaterialListItem])
def list_materials(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return material_service.list_materials(db, user)


@router.get("/{material_id}", response_model=MaterialOut)
def get_material(material_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = material_service.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    ensure_material_visible(user, material)
    return material


@router.put("/{material_id}", response_model=MaterialOut)
def update_material(material_id: str, body: MaterialUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = material_service.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material.submitter_id != user.id:
        raise HTTPException(status_code=403, detail="Not your material")
    if material.status.value not in ("draft", "returned"):
        raise HTTPException(status_code=400, detail="Can only edit draft or returned materials")
    return material_service.update_material(db, material_id, body)


@router.get("/{material_id}/versions")
def get_versions(material_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = material_service.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    ensure_material_visible(user, material)
    return {"versions": material_service.get_material_versions(db, material_id)}


@router.post("/{material_id}/archive", response_model=MaterialOut)
def archive_material(material_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = material_service.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material.submitter_id != user.id:
        raise HTTPException(status_code=403, detail="Not your material")
    if material.status.value not in ("draft", "returned"):
        raise HTTPException(status_code=400, detail="只有草稿和已退回的物料可以归档")
    material.status = MaterialStatus.archived
    material.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(material)
    return material


@router.delete("/{material_id}", status_code=204)
def delete_material(material_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = material_service.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material.submitter_id != user.id:
        raise HTTPException(status_code=403, detail="Not your material")
    if material.status != MaterialStatus.draft:
        raise HTTPException(status_code=400, detail="只有草稿状态的物料可以删除")

    review_count = db.query(Review).filter(Review.material_id == material_id).count()
    if review_count > 0:
        raise HTTPException(status_code=400, detail="该物料已有审查记录，不能物理删除。请使用归档功能。")

    db.delete(material)
    db.commit()
    return Response(status_code=204)
