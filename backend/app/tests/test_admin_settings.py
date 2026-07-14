from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.models.admin import SecureSetting
from app.models.user import User, UserRole
from app.services import admin_settings_service, deepseek_gateway


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _admin() -> User:
    return User(
        id="admin-settings-1",
        username="admin-settings",
        password="not-used",
        display_name="管理员",
        role=UserRole.admin,
        dept_name="管理部",
    )


def test_api_key_is_encrypted_and_never_returned(monkeypatch):
    factory = _session_factory()
    db = factory()
    admin = _admin()
    db.add(admin)
    db.commit()
    monkeypatch.setattr(deepseek_gateway, "validate_api_key", lambda _key: None)
    fake_key = "unit-test-deepseek-key-1234"

    record = admin_settings_service.save_api_key(db, fake_key, admin)
    assert fake_key not in record.encrypted_value
    assert record.fingerprint == "1234"
    assert admin_settings_service.get_api_key(db) == fake_key

    status = admin_settings_service.get_ai_config_status(db)
    assert status.configured is True
    assert status.source == "database"
    assert status.masked_key.endswith("1234")
    assert fake_key not in status.model_dump_json()

    admin_settings_service.clear_api_key(db, admin)
    assert db.query(SecureSetting).count() == 0
    db.close()


def test_failed_validation_does_not_replace_existing_key(monkeypatch):
    factory = _session_factory()
    db = factory()
    admin = _admin()
    db.add(admin)
    db.commit()
    monkeypatch.setattr(deepseek_gateway, "validate_api_key", lambda _key: None)
    admin_settings_service.save_api_key(db, "existing-test-key-0001", admin)

    def reject(_key):
        raise deepseek_gateway.DeepSeekGatewayError("认证失败", category="authentication")

    monkeypatch.setattr(deepseek_gateway, "validate_api_key", reject)
    with pytest.raises(deepseek_gateway.DeepSeekGatewayError):
        admin_settings_service.save_api_key(db, "replacement-test-key-0002", admin)
    assert admin_settings_service.get_api_key(db) == "existing-test-key-0001"
    db.close()


def test_gateway_uses_fixed_model_and_json_output(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(deepseek_gateway, "OpenAI", FakeClient)
    deepseek_gateway.validate_api_key("unit-test-key")

    assert captured["model"] == "deepseek-v4-flash"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["client"]["base_url"] == "https://api.deepseek.com"


def test_gateway_rejects_invalid_json(monkeypatch):
    class FakeClient:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_call: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))]
                    )
                )
            )

    monkeypatch.setattr(deepseek_gateway, "OpenAI", FakeClient)
    with pytest.raises(deepseek_gateway.DeepSeekGatewayError) as exc_info:
        deepseek_gateway.validate_api_key("unit-test-key")
    assert exc_info.value.category == "invalid_response"


def test_legacy_deepseek_environment_fields_are_accepted_but_ignored(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://legacy.invalid")
    monkeypatch.setenv("DEEPSEEK_MODEL", "legacy-model")

    settings = Settings(_env_file=None)

    assert "DEEPSEEK_BASE_URL" not in settings.model_dump()
    assert "DEEPSEEK_MODEL" not in settings.model_dump()
    assert deepseek_gateway.FIXED_BASE_URL == "https://api.deepseek.com"
    assert deepseek_gateway.FIXED_MODEL == "deepseek-v4-flash"


def test_unrelated_unknown_configuration_is_still_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DEEPSEEK_MODELL="typo")
