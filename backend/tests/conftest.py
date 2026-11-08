"""Test harness.

The environment is configured *before* any backend module is imported, because
`backend.config.settings` is resolved once at import time.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Default to a throwaway SQLite file. Set TEST_DATABASE_URL to run the whole
# suite against PostgreSQL instead (what production uses).
_DB_FD, _DB_PATH = tempfile.mkstemp(prefix="synapse-test-", suffix=".db")
os.close(_DB_FD)
_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB_PATH}"

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "SECRET_KEY": "test-secret-key-not-used-anywhere-else",
        "DATABASE_URL": _TEST_DB_URL,
        "ALLOWED_ORIGINS": "http://localhost:5173",
        "ACCESS_TOKEN_MINUTES": "30",
        "REFRESH_TOKEN_DAYS": "14",
        "COOKIE_SECURE": "false",
        "COOKIE_SAMESITE": "lax",
        "ENABLE_DOCS": "true",
        "AUTO_CREATE_TABLES": "true",
        "RUN_MIGRATIONS_ON_STARTUP": "false",
        # Generous defaults so ordinary tests are never rate limited; the
        # rate-limit tests tighten these per-call instead.
        "LOGIN_RATE_LIMIT": "50",
        "REGISTER_RATE_LIMIT": "200",
        "API_RATE_LIMIT": "100000",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.database.connection import Base, SessionLocal, engine  # noqa: E402
from backend.database import models  # noqa: E402,F401
from backend.main import app  # noqa: E402
from backend.security import ratelimit  # noqa: E402
from backend.security.cookies import CSRF_COOKIE, CSRF_HEADER  # noqa: E402

Base.metadata.create_all(bind=engine)

PASSWORD = "CorrectHorse9"


@pytest.fixture(autouse=True)
def clean_state():
    """Empty every table and reset the rate limiter between tests."""
    ratelimit.reset_all()
    db = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()
    yield
    ratelimit.reset_all()


@pytest.fixture
def client():
    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AuthedClient:
    """A TestClient wrapper that keeps cookies and auto-sends the CSRF header."""

    def __init__(self, client: TestClient, email: str, user_id: str):
        self._client = client
        self.email = email
        self.user_id = user_id

    @property
    def csrf(self) -> str:
        return self._client.cookies.get(CSRF_COOKIE, "")

    def _headers(self, extra: dict | None = None, with_csrf: bool = True) -> dict:
        headers = {"X-Groq-API-Key": "gsk_test_key_never_persisted"}
        if with_csrf:
            headers[CSRF_HEADER] = self.csrf
        headers.update(extra or {})
        return headers

    def get(self, url, **kw):
        kw["headers"] = self._headers(kw.pop("headers", None), with_csrf=False)
        return self._client.get(url, **kw)

    def post(self, url, with_csrf: bool = True, **kw):
        kw["headers"] = self._headers(kw.pop("headers", None), with_csrf=with_csrf)
        return self._client.post(url, **kw)

    def put(self, url, **kw):
        kw["headers"] = self._headers(kw.pop("headers", None))
        return self._client.put(url, **kw)

    def patch(self, url, **kw):
        kw["headers"] = self._headers(kw.pop("headers", None))
        return self._client.patch(url, **kw)

    def delete(self, url, **kw):
        kw["headers"] = self._headers(kw.pop("headers", None))
        return self._client.delete(url, **kw)

    @property
    def raw(self) -> TestClient:
        return self._client


def register(client: TestClient, email: str, password: str = PASSWORD, name: str | None = None) -> AuthedClient:
    payload = {"email": email, "password": password}
    if name:
        payload["full_name"] = name
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return AuthedClient(client, email, response.json()["user"]["id"])


@pytest.fixture
def alice(client):
    return register(client, "alice@example.com")


@pytest.fixture
def bob():
    """A second, fully independent browser session."""
    with TestClient(app, base_url="http://testserver") as other:
        yield register(other, "bob@example.com")


def start_meeting(user: AuthedClient, title: str = "Test Meeting", playbook: str = "general") -> str:
    response = user.post(
        "/api/meeting/start",
        json={"title": title, "playbook": playbook, "meeting_memory": "notes"},
    )
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def replace_cookie(test_client: TestClient, name: str, value: str) -> None:
    """Overwrite a cookie already in the jar, in place.

    httpx stores a host-only cookie under a synthetic domain
    (`testserver.local`), so `cookies.set(name, value)` adds a *second* entry
    instead of replacing the server-issued one. Mutating the existing jar entry
    reproduces what a browser does when the same cookie is overwritten.
    """
    for cookie in test_client.cookies.jar:
        if cookie.name == name:
            cookie.value = value
            return
    test_client.cookies.set(name, value)
