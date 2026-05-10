"""User management endpoints — placeholder for future user system."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class UserProfile(BaseModel):
    id: str
    username: str
    email: str = ""


@router.get("/me", response_model=UserProfile)
async def get_current_user():
    """Placeholder — returns a mock user."""
    raise HTTPException(status_code=501, detail="User management not yet implemented")
