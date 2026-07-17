from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth import hash_password
from app.core.config import get_settings
from app.core.rate_limit import reset_rate_limits


def test_login_returns_user_and_wrong_credentials_remain_normal_401():
    reset_rate_limits()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    db.add(
        User(
            id="login-user-1",
            username="login-user",
            password=hash_password("correct-password"),
            display_name="登录测试",
            role=UserRole.admin,
            dept_name="测试部",
        )
    )
    db.commit()
    db.close()

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        failed = client.post("/api/v1/auth/login", json={"username": "login-user", "password": "wrong"})
        assert failed.status_code == 401
        assert failed.json()["detail"] == "账户或密码错误"

        succeeded = client.post(
            "/api/v1/auth/login",
            json={"username": "login-user", "password": "correct-password"},
        )
        assert succeeded.status_code == 200
        assert succeeded.json()["user"]["id"] == "login-user-1"
        assert succeeded.json()["access_token"]
    finally:
        app.dependency_overrides.clear()
        reset_rate_limits()


def test_repeated_failed_logins_are_rate_limited():
    reset_rate_limits()
    settings = get_settings()
    original_attempts = settings.LOGIN_RATE_LIMIT_ATTEMPTS
    original_window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    settings.LOGIN_RATE_LIMIT_ATTEMPTS = 2
    settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        payload = {"username": "admin", "password": "wrong-password"}
        assert client.post("/api/v1/auth/login", json=payload).status_code == 401
        assert client.post("/api/v1/auth/login", json=payload).status_code == 401

        blocked = client.post("/api/v1/auth/login", json=payload)
        assert blocked.status_code == 429
        assert blocked.json()["detail"] == "登录尝试过于频繁，请稍后再试"
        assert int(blocked.headers["retry-after"]) >= 1
    finally:
        app.dependency_overrides.clear()
        settings.LOGIN_RATE_LIMIT_ATTEMPTS = original_attempts
        settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS = original_window
        reset_rate_limits()
