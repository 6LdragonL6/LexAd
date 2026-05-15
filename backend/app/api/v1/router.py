from fastapi import APIRouter
from app.api.v1.endpoints import auth, materials, reviews, knowledge

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(materials.router, prefix="/materials", tags=["materials"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
