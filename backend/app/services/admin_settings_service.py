from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.admin import SecureSetting
from app.models.knowledge import KnowledgeAuditLog
from app.models.user import User
from app.schemas.admin import AiConfigStatus


DEEPSEEK_SETTING_KEY = "deepseek_api_key"
FIXED_BASE_URL = "https://api.deepseek.com"
FIXED_MODEL = "deepseek-v4-flash"
DEFAULT_SECRET_KEY = "change-me-in-production"


class SecureSettingError(RuntimeError):
    pass


def get_api_key(db: Session) -> str:
    settings = get_settings()
    if settings.COMPETITION_MODE:
        # 竞赛部署必须由 Render 环境变量单向控制，忽略数据库中的旧配置。
        return settings.DEEPSEEK_API_KEY.strip()
    record = _get_record(db)
    if record:
        return _decrypt(record.encrypted_value)
    return settings.DEEPSEEK_API_KEY.strip()


def get_ai_config_status(db: Session) -> AiConfigStatus:
    settings = get_settings()
    if settings.COMPETITION_MODE:
        env_key = settings.DEEPSEEK_API_KEY.strip()
        return AiConfigStatus(
            configured=bool(env_key),
            base_url=FIXED_BASE_URL,
            model=FIXED_MODEL,
            masked_key=_masked(env_key[-4:]) if env_key else "",
            source="environment" if env_key else "none",
            validation_status="competition_environment" if env_key else "unconfigured",
        )
    record = _get_record(db)
    if record:
        return AiConfigStatus(
            configured=True,
            base_url=FIXED_BASE_URL,
            model=FIXED_MODEL,
            masked_key=_masked(record.fingerprint),
            source="database",
            validation_status=record.validation_status,
            last_error=record.last_error,
            updated_at=record.updated_at,
            validated_at=record.validated_at,
            updated_by_id=record.updated_by_id,
        )
    env_key = settings.DEEPSEEK_API_KEY.strip()
    return AiConfigStatus(
        configured=bool(env_key),
        base_url=FIXED_BASE_URL,
        model=FIXED_MODEL,
        masked_key=_masked(env_key[-4:]) if env_key else "",
        source="environment" if env_key else "none",
        validation_status="environment" if env_key else "unconfigured",
    )


def save_api_key(db: Session, api_key: str, actor: User) -> SecureSetting:
    settings = get_settings()
    if settings.APP_ENV == "production" and settings.SECRET_KEY == DEFAULT_SECRET_KEY:
        raise SecureSettingError("生产环境必须先配置安全的 SECRET_KEY")

    from app.services.deepseek_gateway import validate_api_key

    validate_api_key(api_key)
    now = datetime.now(timezone.utc)
    record = _get_record(db)
    if record is None:
        record = SecureSetting(
            key=DEEPSEEK_SETTING_KEY,
            encrypted_value=_encrypt(api_key),
            fingerprint=api_key[-4:],
            validation_status="verified",
            last_error="",
            updated_by_id=actor.id,
            validated_at=now,
        )
        db.add(record)
    else:
        record.encrypted_value = _encrypt(api_key)
        record.fingerprint = api_key[-4:]
        record.validation_status = "verified"
        record.last_error = ""
        record.updated_by_id = actor.id
        record.updated_at = now
        record.validated_at = now
    _audit(db, actor.id, "ai_config.update", "配置已验证并更新")
    db.commit()
    db.refresh(record)
    return record


def clear_api_key(db: Session, actor: User) -> None:
    record = _get_record(db)
    if record:
        db.delete(record)
    _audit(db, actor.id, "ai_config.clear", "已清除数据库中的 API 配置")
    db.commit()


def _get_record(db: Session) -> SecureSetting | None:
    return db.query(SecureSetting).filter(SecureSetting.key == DEEPSEEK_SETTING_KEY).first()


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def _decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise SecureSettingError("API 配置无法解密，请管理员重新保存") from exc


def _masked(fingerprint: str) -> str:
    return f"••••••••{fingerprint}" if fingerprint else ""


def _audit(db: Session, actor_id: str, action: str, message: str) -> None:
    db.add(
        KnowledgeAuditLog(
            actor_id=actor_id,
            action=action,
            target_type="secure_setting",
            target_id=DEEPSEEK_SETTING_KEY,
            before_state={},
            after_state={},
            message=message,
        )
    )
