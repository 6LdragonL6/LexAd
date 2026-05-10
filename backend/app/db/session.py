"""Database session management with Neon PostgreSQL support."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def _build_engine():
    db_url = settings.DATABASE_URL
    if not db_url:
        # Use SQLite for local development when no DATABASE_URL is set
        return create_engine(
            "sqlite:///./lexad.db", connect_args={"check_same_thread": False}, echo=False
        )
    return create_engine(
        db_url,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=False,
    )


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
