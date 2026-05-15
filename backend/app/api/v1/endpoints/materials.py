from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.material import MaterialSubmit, MaterialUpdate, MaterialOut, MaterialListItem
from app.services import material_service

router = APIRouter()

@router.post("/submit", response_model=MaterialOut, status_code=201)
def submit_material(body: MaterialSubmit, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = material_service.create_material(db, body, user.id)
    return material

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
