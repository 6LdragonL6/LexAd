from datetime import datetime, timezone
import json
from pathlib import Path

from app.core.config import Settings
from app.schemas.review import ReviewOut
from app.schemas.review_progress import build_review_stages


def _review_payload(**overrides):
    payload = {
        "id": "review-1",
        "material_id": "material-1",
        "version": 1,
        "legal_compliance_score": 88,
        "public_opinion_safety_score": 72,
        "ai_result": {},
        "task_status": "processing",
        "error_message": None,
        "started_at": None,
        "completed_at": None,
        "legal_module_status": "running",
        "public_opinion_module_status": "pending",
        "public_opinion_result": {},
        "legal_decision": None,
        "legal_notes": None,
        "return_reasons": None,
        "reviewer_id": None,
        "reviewed_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return payload


def test_review_contract_uses_explicit_higher_is_better_scores():
    serialized = ReviewOut.model_validate(_review_payload()).model_dump()

    assert serialized["legal_compliance_score"] == 88
    assert serialized["public_opinion_safety_score"] == 72
    assert "ai_risk_score" not in serialized
    assert "risk_score" not in serialized


def test_review_progress_tracks_real_module_states():
    stages = build_review_stages(
        task_status="processing",
        legal_module_status="succeeded",
        public_opinion_module_status="running",
        ai_result={},
        public_opinion_result={},
    )

    assert [stage["status"] for stage in stages] == [
        "completed",
        "completed",
        "running",
        "pending",
    ]


def test_review_progress_exposes_manual_review_without_fake_completion():
    stages = build_review_stages(
        task_status="completed",
        legal_module_status="succeeded",
        public_opinion_module_status="succeeded",
        ai_result={"requires_manual_review": True},
        public_opinion_result={"status": "manual_review", "requires_manual_review": True},
    )

    assert [stage["status"] for stage in stages] == [
        "completed",
        "manual_review",
        "manual_review",
        "completed",
    ]


def test_review_progress_marks_summary_failed_when_task_fails():
    stages = build_review_stages(
        task_status="failed",
        legal_module_status="failed",
        public_opinion_module_status="pending",
        ai_result={},
        public_opinion_result={},
    )

    assert stages[1]["status"] == "failed"
    assert stages[-1]["status"] == "failed"


def test_v072_version_is_consistent_across_runtime_surfaces():
    repository_root = Path(__file__).resolve().parents[3]
    package = json.loads((repository_root / "frontend" / "package.json").read_text(encoding="utf-8"))
    frontend_constant = (repository_root / "frontend" / "src" / "constants" / "app.ts").read_text(encoding="utf-8")

    assert Settings().APP_VERSION == "0.7.2"
    assert package["version"] == "0.7.2"
    assert "APP_VERSION = '0.7.2'" in frontend_constant
