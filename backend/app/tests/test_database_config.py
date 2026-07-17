"""测试显式数据库模式配置 —— 验证解析逻辑和拒绝条件。"""

import os
import pytest

from app.core.config import Settings, get_settings
from app.db.url import resolve_database_url, database_target_label, is_sqlite_url


def _settings(**overrides) -> Settings:
    """构建测试用的 Settings，所有字段使用非 .env 默认值，然后覆盖。"""
    base = {
        "DATABASE_MODE": "local",
        "LOCAL_DATABASE_URL": "sqlite:///./lexad.db",
        "DATABASE_URL": "",
    }
    base.update(overrides)
    return Settings(**base)


class TestResolveDatabaseUrl:
    def test_local_returns_local_sqlite(self):
        s = _settings(DATABASE_MODE="local")
        assert resolve_database_url(s) == "sqlite:///./lexad.db"

    def test_local_ignores_neon_url(self):
        s = _settings(
            DATABASE_MODE="local",
            DATABASE_URL="postgresql://user:pass@host/db",
        )
        assert resolve_database_url(s) == "sqlite:///./lexad.db"

    def test_neon_requires_url(self):
        s = _settings(DATABASE_MODE="neon", DATABASE_URL="")
        with pytest.raises(RuntimeError, match="DATABASE_URL 未设置"):
            resolve_database_url(s)

    def test_neon_rejects_sqlite_url(self):
        s = _settings(
            DATABASE_MODE="neon",
            DATABASE_URL="sqlite:///./lexad.db",
        )
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            resolve_database_url(s)

    def test_local_rejects_postgresql_url(self):
        s = _settings(
            DATABASE_MODE="local",
            LOCAL_DATABASE_URL="postgresql://user:pass@host/db",
        )
        with pytest.raises(RuntimeError, match="SQLite"):
            resolve_database_url(s)

    def test_neon_accepts_postgresql_url(self):
        s = _settings(
            DATABASE_MODE="neon",
            DATABASE_URL="postgresql://user:pass@host/db",
        )
        assert resolve_database_url(s) == "postgresql://user:pass@host/db"


class TestDatabaseTargetLabel:
    def test_label_never_leaks_url(self):
        s = _settings(
            DATABASE_MODE="neon",
            DATABASE_URL="postgresql://user:secret@ep-xyz.us-east-2.aws.neon.tech/db?sslmode=require",
        )
        label = database_target_label(s)
        assert "user" not in label
        assert "secret" not in label
        assert "ep-xyz" not in label
        assert label == "Neon PostgreSQL"

    def test_local_label(self):
        s = _settings(DATABASE_MODE="local")
        assert database_target_label(s) == "local SQLite"


class TestIsSqliteUrl:
    def test_sqlite_detected(self):
        assert is_sqlite_url("sqlite:///./lexad.db")

    def test_postgresql_not_sqlite(self):
        assert not is_sqlite_url("postgresql://user:pass@host/db")


class TestProductionRequiresNeon:
    def test_production_with_local_fails(self):
        with pytest.raises(ValueError, match="production"):
            Settings(
                APP_ENV="production",
                DATABASE_MODE="local",
            )

    def test_production_demo_seed_rejects_default_passwords(self):
        with pytest.raises(ValueError, match="至少 12 位"):
            Settings(
                APP_ENV="production",
                DATABASE_MODE="neon",
                DATABASE_URL="postgresql://user:pass@host/db",
                DEMO_SEED_ENABLED=True,
                DEMO_ADMIN_PASSWORD="admin123",
                DEMO_MARKETING_PASSWORD="test1234",
                DEMO_LEGAL_PASSWORD="test1234",
            )

    def test_production_demo_seed_accepts_distinct_strong_admin_password(self):
        settings = Settings(
            APP_ENV="production",
            DATABASE_MODE="neon",
            DATABASE_URL="postgresql://user:pass@host/db",
            DEMO_SEED_ENABLED=True,
            DEMO_ADMIN_PASSWORD="admin-strong-password-2026",
            DEMO_MARKETING_PASSWORD="market-strong-password-2026",
            DEMO_LEGAL_PASSWORD="legal-strong-password-2026",
        )
        assert settings.DEMO_SEED_ENABLED is True
