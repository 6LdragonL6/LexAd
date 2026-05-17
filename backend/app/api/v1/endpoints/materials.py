import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.material import MaterialSubmit, MaterialUpdate, MaterialOut, MaterialListItem, PreviewTextResponse
from app.services import material_service
from app.services.file_extraction import FileExtractionService, ExtractionError
from app.storage import save_upload_temp, cleanup_temp

router = APIRouter()
_extraction_svc = FileExtractionService()

SUPPORTED_FORMATS = "JPG/PNG/GIF/BMP/PDF/DOCX/DOC/PPTX/XLSX/TXT"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/submit", response_model=MaterialOut, status_code=201)
async def submit_material(
    body: str = Form(...),
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = MaterialSubmit(**json.loads(body))
    extracted_text = ""

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
            result = _extraction_svc.extract(tmp_path, mime)
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

    material = material_service.create_material(db, data, user.id, extracted_text)
    return material


@router.post("/preview-text", response_model=PreviewTextResponse)
async def preview_text(
    file: UploadFile = File(...),
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
        result = _extraction_svc.extract(tmp_path, mime)
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
    content = file.file.read()
    file.file.seek(0)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="文件过大（上限 10MB），请压缩后重试",
        )


@router.get("/list", response_model=list[MaterialListItem])
def list_materials(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return material_service.list_materials(db, user)


@router.get("/{material_id}", response_model=MaterialOut)
def get_material(material_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = material_service.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
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
    return {"versions": material_service.get_material_versions(db, material_id)}
