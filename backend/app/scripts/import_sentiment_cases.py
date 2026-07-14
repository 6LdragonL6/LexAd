"""Import the project sentiment case file through the shared normalizer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.services.public_opinion_case_service import BUILTIN_CASES_PATH, sync_case_file


def import_sentiment_cases(input_path: str, admin_id: str) -> dict:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Sentiment cases file not found: {path}")
    db = SessionLocal()
    try:
        actor = db.query(User).filter(User.id == admin_id).first()
        if not actor:
            raise ValueError(f"Admin user not found: {admin_id}")
        result = sync_case_file(db, actor, path, import_source="cli_sentiment_cases")
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import LexAd sentiment cases")
    parser.add_argument("--input", "-i", default=str(BUILTIN_CASES_PATH), help="Path to sentiment_cases.json")
    parser.add_argument("--admin-id", default=None, help="Admin user ID (defaults to first admin)")
    args = parser.parse_args()

    if not args.admin_id:
        db = SessionLocal()
        try:
            admin = db.query(User).filter(User.role == UserRole.admin).order_by(User.created_at.asc()).first()
            if not admin:
                raise ValueError("No admin user found")
            args.admin_id = admin.id
        finally:
            db.close()

    result = import_sentiment_cases(args.input, args.admin_id)
    print(
        "Import complete: "
        f"{result['created']} created, {result['updated']} updated, {result['skipped']} skipped; "
        f"canonical cases={result['canonical_count']}."
    )


if __name__ == "__main__":
    main()
