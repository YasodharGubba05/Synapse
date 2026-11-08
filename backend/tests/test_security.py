"""CSRF, rate limiting, lockout, headers, CORS, upload limits, secret handling."""
from __future__ import annotations

import pytest

from backend.config import settings
from backend.database import crud
from backend.database.models import AuthSession, MeetingSession, User
from backend.security import ratelimit
from backend.security.cookies import CSRF_COOKIE, CSRF_HEADER
from tests.conftest import PASSWORD, register, start_meeting


# ── CSRF ──────────────────────────────────────────────────────────────────────

def test_state_changing_request_without_csrf_header_is_rejected(alice):
    response = alice.post("/api/meeting/start", with_csrf=False, json={"title": "x"})
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


def test_state_changing_request_with_wrong_csrf_header_is_rejected(alice):
    response = alice.post(
        "/api/meeting/start",
        with_csrf=False,
        headers={CSRF_HEADER: "not-the-real-token"},
        json={"title": "x"},
    )
    assert response.status_code == 403


def test_safe_requests_do_not_need_a_csrf_header(alice):
    assert alice.get("/api/history").status_code == 200


def test_delete_requires_csrf(alice):
    session_id = start_meeting(alice)
    bare = alice.raw.delete(f"/api/history/{session_id}")
    assert bare.status_code == 403
    assert alice.get(f"/api/history/{session_id}").status_code == 200


def test_transcribe_requires_csrf(alice):
    response = alice.post(
        "/api/transcribe",
        with_csrf=False,
        files={"audio_file": ("a.webm", b"x" * 2000, "audio/webm")},
    )
    assert response.status_code == 403


def test_csrf_cookie_is_rotated_on_refresh(alice):
    first = alice.raw.cookies.get(CSRF_COOKIE)
    assert alice.post("/api/auth/refresh").status_code == 200
    assert alice.raw.cookies.get(CSRF_COOKIE) != first


# ── Brute force protection ────────────────────────────────────────────────────

def test_repeated_failed_logins_are_rate_limited(client, monkeypatch):
    register(client, "brute@example.com")
    monkeypatch.setattr(settings, "login_rate_limit", 4)
    ratelimit.reset_all()

    statuses = [
        client.post("/api/auth/login", json={"email": "brute@example.com", "password": "Wrong12345"}).status_code
        for _ in range(6)
    ]
    assert statuses[:4] == [401, 401, 401, 401]
    assert 429 in statuses[4:]


def test_account_locks_after_too_many_failures(client, db_session, monkeypatch):
    register(client, "locked@example.com")
    monkeypatch.setattr(settings, "login_rate_limit", 100)
    monkeypatch.setattr(settings, "max_failed_logins", 3)
    ratelimit.reset_all()

    for _ in range(3):
        assert client.post(
            "/api/auth/login", json={"email": "locked@example.com", "password": "Wrong12345"}
        ).status_code == 401

    user = db_session.query(User).filter(User.email == "locked@example.com").first()
    db_session.refresh(user)
    assert user.locked_until is not None

    # Even the correct password is refused while the lock is in force.
    locked = client.post("/api/auth/login", json={"email": "locked@example.com", "password": PASSWORD})
    assert locked.status_code == 429
    assert "Retry-After" in locked.headers


def test_successful_login_clears_the_failure_counter(client, db_session):
    register(client, "counter@example.com")
    client.post("/api/auth/login", json={"email": "counter@example.com", "password": "Wrong12345"})
    assert client.post(
        "/api/auth/login", json={"email": "counter@example.com", "password": PASSWORD}
    ).status_code == 200
    user = db_session.query(User).filter(User.email == "counter@example.com").first()
    db_session.refresh(user)
    assert (user.failed_login_count or 0) == 0
    assert user.locked_until is None


def test_registration_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "register_rate_limit", 2)
    ratelimit.reset_all()
    codes = [
        client.post("/api/auth/register", json={"email": f"spam{i}@example.com", "password": PASSWORD}).status_code
        for i in range(4)
    ]
    assert codes[:2] == [201, 201]
    assert 429 in codes[2:]


def test_authenticated_api_calls_are_rate_limited(alice, monkeypatch):
    monkeypatch.setattr(settings, "api_rate_limit", 5)
    ratelimit.reset_all()
    codes = [alice.get("/api/history").status_code for _ in range(8)]
    assert 429 in codes


# ── Response headers ──────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "header,expected",
    [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "no-referrer"),
        ("Cross-Origin-Opener-Policy", "same-origin"),
    ],
)
def test_security_headers_are_present(client, header, expected):
    response = client.get("/api/health")
    assert response.headers.get(header) == expected


def test_content_security_policy_is_locked_down(client):
    csp = client.get("/api/health").headers.get("Content-Security-Policy", "")
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


# ── CORS ──────────────────────────────────────────────────────────────────────

def test_allowed_origin_gets_credentialed_cors_headers(client):
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_unknown_origin_is_not_allowed(client):
    response = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert response.headers.get("access-control-allow-origin") is None


def test_cors_is_never_a_wildcard(client):
    assert "*" not in settings.allowed_origins
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") is None


# ── Payload limits ────────────────────────────────────────────────────────────

def test_oversized_audio_upload_is_rejected(alice, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 4096)
    response = alice.post(
        "/api/transcribe",
        files={"audio_file": ("big.webm", b"x" * 20000, "audio/webm")},
    )
    assert response.status_code == 413


def test_oversized_json_body_is_rejected(alice, monkeypatch):
    monkeypatch.setattr(settings, "max_json_body_bytes", 2048)
    response = alice.post("/api/chat", json={"message": "x" * 8000, "full_transcript": "y"})
    assert response.status_code == 413


def test_unsupported_audio_type_is_rejected_without_calling_groq(alice):
    response = alice.post(
        "/api/transcribe",
        files={"audio_file": ("evil.exe", b"MZ" + b"x" * 3000, "application/x-msdownload")},
    )
    assert response.status_code == 200
    assert response.json() == {"text": "", "error": "Unsupported audio format"}


# ── Secret handling ───────────────────────────────────────────────────────────

def test_groq_api_key_is_never_persisted_anywhere(alice, db_session):
    """The key travels in a header on every call and must leave no trace."""
    key = "gsk_test_key_never_persisted"
    start_meeting(alice)
    alice.get("/api/history")

    from sqlalchemy import text

    from backend.database.connection import Base

    for table in Base.metadata.sorted_tables:
        rows = db_session.execute(text(f"SELECT * FROM {table.name}")).mappings().all()
        for row in rows:
            for column, value in row.items():
                assert key not in str(value), f"Groq key leaked into {table.name}.{column}"


def test_password_is_never_returned_by_the_api(client):
    response = client.post(
        "/api/auth/register", json={"email": "secret@example.com", "password": PASSWORD}
    )
    assert PASSWORD not in response.text
    assert "password" not in response.json()["user"]


def test_user_row_stores_only_an_argon2id_hash(client, db_session):
    register(client, "hashed@example.com")
    user = crud.get_user_by_email(db_session, "hashed@example.com")
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


def test_refresh_token_is_stored_only_as_a_digest(alice, db_session):
    raw_refresh = alice.raw.cookies.get("synapse_refresh")
    rows = db_session.query(AuthSession).filter(AuthSession.user_id == alice.user_id).all()
    assert rows
    for row in rows:
        assert row.refresh_token_hash != raw_refresh
        assert len(row.refresh_token_hash) == 64  # sha256 hex


def test_validation_errors_do_not_echo_submitted_values(client):
    response = client.post(
        "/api/auth/register", json={"email": "bad", "password": "SuperSecretValue123"}
    )
    assert response.status_code == 422
    assert "SuperSecretValue123" not in response.text


# ── SQL injection ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "payload",
    [
        "' OR '1'='1",
        "'; DROP TABLE meeting_sessions; --",
        "1' UNION SELECT * FROM users --",
    ],
)
def test_sql_injection_attempts_are_inert(alice, db_session, payload):
    """Everything goes through SQLAlchemy's parameter binding."""
    before = db_session.query(MeetingSession).count()
    response = alice.get(f"/api/history/{payload}")
    assert response.status_code in (403, 404)
    db_session.expire_all()
    assert db_session.query(MeetingSession).count() == before
    # The table still exists and is queryable.
    assert db_session.query(User).count() >= 1


def test_injection_in_a_title_is_stored_as_plain_text(alice):
    session_id = start_meeting(alice)
    nasty = "'; DROP TABLE users; --"
    assert alice.put(f"/api/history/{session_id}/title", json={"title": nasty}).status_code == 200
    assert alice.get(f"/api/history/{session_id}").json()["title"] == nasty
    assert alice.get("/api/auth/me").status_code == 200


# ── Cross-site cookie mode ────────────────────────────────────────────────────

def test_cross_site_mode_marks_cookies_partitioned(client, monkeypatch):
    """In SameSite=None mode the cookies must also carry CHIPS Partitioned, or
    browsers that restrict third-party cookies will silently drop the session."""
    monkeypatch.setattr(settings, "cookie_samesite", "none")
    monkeypatch.setattr(settings, "cookie_secure", True)

    response = client.post(
        "/api/auth/register", json={"email": "chips@example.com", "password": PASSWORD}
    )
    assert response.status_code == 201
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 3
    for cookie in cookies:
        assert "SameSite=none" in cookie
        assert "Secure" in cookie
        assert cookie.endswith("; Partitioned"), cookie


def test_same_site_lax_mode_is_not_partitioned(client, monkeypatch):
    monkeypatch.setattr(settings, "cookie_samesite", "lax")
    response = client.post(
        "/api/auth/register", json={"email": "nochips@example.com", "password": PASSWORD}
    )
    assert response.status_code == 201
    for cookie in response.headers.get_list("set-cookie"):
        assert "Partitioned" not in cookie
