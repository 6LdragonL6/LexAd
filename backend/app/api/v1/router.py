from fastapi import APIRouter
from app.api.v1.endpoints import admin_knowledge, auth, brands, materials, reviews, knowledge

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(brands.router, prefix="/brands", tags=["brands"])
api_router.include_router(materials.router, prefix="/materials", tags=["materials"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(admin_knowledge.router, prefix="/admin/knowledge", tags=["admin-knowledge"])
