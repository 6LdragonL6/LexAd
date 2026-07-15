import json
from pathlib import Path
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PREVIOUS_REVISION = "b8d4e1f7a203"
CURRENT_REVISION = "c9e7a1b4d2f0"


def _alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


def _json_value(value):
    return json.loads(value) if isinstance(value, str) else value


def test_v072_score_migration_upgrade_downgrade_cycle(monkeypatch):
    database_path = BACKEND_ROOT / f"v072-migration-{uuid.uuid4().hex}.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_MODE", "local")
    monkeypatch.setenv("LOCAL_DATABASE_URL", database_url)
    monkeypatch.chdir(BACKEND_ROOT)
    get_settings.cache_clear()
    config = _alembic_config()

    try:
        command.upgrade(config, PREVIOUS_REVISION)
        engine = create_engine(database_url)
        with engine.begin() as connection:
            common = {
                "material_id": "missing-material",
                "version": 1,
                "ai_risk_score": 82,
                "ai_result": json.dumps({"summary": "保留法规证据"}, ensure_ascii=False),
                "task_status": "completed",
                "created_at": "2026-07-15 00:00:00",
            }
            connection.execute(
                text(
                    "INSERT INTO reviews "
                    "(id, material_id, version, ai_risk_score, ai_result, task_status, "
                    "public_opinion_module_status, public_opinion_result, created_at) "
                    "VALUES (:id, :material_id, :version, :ai_risk_score, :ai_result, :task_status, "
                    ":public_status, :public_result, :created_at)"
                ),
                [
                    {
                        **common,
                        "id": "reliable",
                        "public_status": "succeeded",
                        "public_result": json.dumps(
                            {"status": "succeeded", "risk_score": 70, "evidence_quotes": ["原文证据"]},
                            ensure_ascii=False,
                        ),
                    },
                    {
                        **common,
                        "id": "manual",
                        "public_status": "succeeded",
                        "public_result": json.dumps(
                            {"status": "manual_review", "risk_score": 0, "requires_manual_review": True},
                            ensure_ascii=False,
                        ),
                    },
                ],
            )

        command.upgrade(config, CURRENT_REVISION)
        columns = {column["name"] for column in inspect(engine).get_columns("reviews")}
        assert "legal_compliance_score" in columns
        assert "public_opinion_safety_score" in columns
        assert "ai_risk_score" not in columns

        with engine.connect() as connection:
            rows = {
                row.id: row
                for row in connection.execute(
                    text(
                        "SELECT id, legal_compliance_score, public_opinion_safety_score, "
                        "public_opinion_result FROM reviews"
                    )
                )
            }
        assert rows["reliable"].legal_compliance_score == 82
        assert rows["reliable"].public_opinion_safety_score == 30
        assert rows["manual"].public_opinion_safety_score is None
        assert _json_value(rows["reliable"].public_opinion_result) == {
            "status": "succeeded",
            "evidence_quotes": ["原文证据"],
        }
        assert "risk_score" not in _json_value(rows["manual"].public_opinion_result)

        command.downgrade(config, PREVIOUS_REVISION)
        downgraded_columns = {column["name"] for column in inspect(engine).get_columns("reviews")}
        assert "ai_risk_score" in downgraded_columns
        assert "public_opinion_safety_score" not in downgraded_columns
        with engine.connect() as connection:
            restored = connection.execute(
                text("SELECT ai_risk_score, public_opinion_result FROM reviews WHERE id = 'reliable'")
            ).one()
        assert restored.ai_risk_score == 82
        assert _json_value(restored.public_opinion_result)["risk_score"] == 70

        command.upgrade(config, CURRENT_REVISION)
        with engine.connect() as connection:
            repeated = connection.execute(
                text(
                    "SELECT legal_compliance_score, public_opinion_safety_score "
                    "FROM reviews WHERE id = 'reliable'"
                )
            ).one()
        assert repeated.legal_compliance_score == 82
        assert repeated.public_opinion_safety_score == 30
    finally:
        get_settings.cache_clear()
        if "engine" in locals():
            engine.dispose()
        database_path.unlink(missing_ok=True)
