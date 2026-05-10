"""Authentication endpoints — placeholder for future auth system."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(_body: LoginRequest):
    """Placeholder login — returns a mock token."""
    raise HTTPException(status_code=501, detail="Authentication not yet implemented")


@router.post("/register")
async def register():
    """Placeholder registration."""
    raise HTTPException(status_code=501, detail="Registration not yet implemented")
