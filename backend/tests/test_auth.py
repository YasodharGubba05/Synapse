"""Registration, login, logout, session persistence and refresh."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.config import settings
from backend.database import crud
from backend.database.models import AuthSession, User
from backend.security.cookies import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER, REFRESH_COOKIE
from backend.security.ratelimit import reset_all
from tests.conftest import PASSWORD, register, replace_cookie


# ── Registration ──────────────────────────────────────────────────────────────

def test_register_creates_account_and_logs_in(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={"email": "New.User@Example.com", "password": PASSWORD, "full_name": "New User"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["email"] == "new.user@example.com"  # normalised
    assert body["expires_in"] == settings.access_token_minutes * 60
    assert "password" not in response.text.lower()

    # All three cookies are issued; the two credentials are HTTP-only.
    set_cookies = response.headers.get_list("set-cookie")
    joined = " ".join(set_cookies)
    assert ACCESS_COOKIE in joined and REFRESH_COOKIE in joined and CSRF_COOKIE in joined
    access_cookie = next(c for c in set_cookies if c.startswith(ACCESS_COOKIE))
    refresh_cookie = next(c for c in set_cookies if c.startswith(REFRESH_COOKIE))
    csrf_cookie = next(c for c in set_cookies if c.startswith(CSRF_COOKIE))
    assert "HttpOnly" in access_cookie and "HttpOnly" in refresh_cookie
    assert "HttpOnly" not in csrf_cookie  # the client must be able to read it

    user = crud.get_user_by_email(db_session, "new.user@example.com")
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


def test_register_rejects_duplicate_email(client):
    register(client, "dupe@example.com")
    response = client.post("/api/auth/register", json={"email": "DUPE@example.com", "password": PASSWORD})
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.parametrize(
    "password",
    ["short1", "nodigitsatall", "1234567890", " leadingspace1"],
)
def test_register_enforces_password_policy(client, password):
    response = client.post("/api/auth/register", json={"email": "weak@example.com", "password": password})
    assert response.status_code == 422, response.text
    assert password not in response.text  # the submitted value is not echoed


def test_register_rejects_invalid_email(client):
    response = client.post("/api/auth/register", json={"email": "not-an-email", "password": PASSWORD})
    assert response.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_succeeds_and_sets_session(client):
    register(client, "login@example.com")
    client.cookies.clear()
    response = client.post("/api/auth/login", json={"email": "login@example.com", "password": PASSWORD})
    assert response.status_code == 200, response.text
    assert response.json()["user"]["email"] == "login@example.com"
    assert client.cookies.get(ACCESS_COOKIE)


def test_login_rejects_wrong_password(client):
    register(client, "wrong@example.com")
    response = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "TotallyWrong1"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_rejects_unknown_email_with_same_message(client):
    response = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD})
    assert response.status_code == 401
    # Identical wording: no account enumeration through the error text.
    assert response.json()["detail"] == "Incorrect email or password"


# ── Session persistence & logout ──────────────────────────────────────────────

def test_me_returns_current_user(alice):
    response = alice.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_session_survives_a_fresh_request_cycle(alice):
    """Equivalent of a browser refresh: cookies alone re-establish the session."""
    for _ in range(3):
        assert alice.get("/api/auth/me").status_code == 200


def test_logout_revokes_the_session_immediately(alice, db_session):
    access_before = alice.raw.cookies.get(ACCESS_COOKIE)
    assert alice.post("/api/auth/logout").status_code == 200
    assert alice.get("/api/auth/me").status_code == 401

    rows = db_session.query(AuthSession).filter(AuthSession.user_id == alice.user_id).all()
    assert rows and all(row.revoked_at is not None for row in rows)

    # Even replaying the captured (still unexpired) access cookie fails, because
    # the server-side auth session it names is revoked.
    replace_cookie(alice.raw, ACCESS_COOKIE, access_before)
    assert alice.raw.get("/api/auth/me").status_code == 401


def test_logout_without_cookies_is_a_no_op(client):
    assert client.post("/api/auth/logout").status_code == 200


# ── Refresh & rotation ────────────────────────────────────────────────────────

def test_refresh_rotates_tokens(alice):
    old_refresh = alice.raw.cookies.get(REFRESH_COOKIE)
    time.sleep(1.1)  # JWT iat/exp have one-second resolution
    response = alice.post("/api/auth/refresh")
    assert response.status_code == 200, response.text
    new_refresh = alice.raw.cookies.get(REFRESH_COOKIE)
    assert new_refresh and new_refresh != old_refresh
    assert alice.get("/api/auth/me").status_code == 200


def test_replaying_a_rotated_refresh_token_kills_every_session(alice, db_session):
    old_refresh = alice.raw.cookies.get(REFRESH_COOKIE)
    time.sleep(1.1)
    assert alice.post("/api/auth/refresh").status_code == 200

    replace_cookie(alice.raw, REFRESH_COOKIE, old_refresh)
    replay = alice.post("/api/auth/refresh")
    assert replay.status_code == 401

    rows = db_session.query(AuthSession).filter(AuthSession.user_id == alice.user_id).all()
    assert rows and all(row.revoked_at is not None for row in rows)


def test_refresh_without_cookie_is_unauthorized(client):
    client.cookies.set(CSRF_COOKIE, "x")
    response = client.post("/api/auth/refresh", headers={CSRF_HEADER: "x"})
    assert response.status_code == 401


def test_expired_access_token_is_rejected_then_recoverable_via_refresh(alice, db_session):
    """An expired access cookie fails closed; the refresh cookie restores access."""
    auth_session = db_session.query(AuthSession).filter(AuthSession.user_id == alice.user_id).first()
    expired = jwt.encode(
        {
            "sub": alice.user_id,
            "sid": auth_session.id,
            "type": "access",
            "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
            "jti": "expired",
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    replace_cookie(alice.raw, ACCESS_COOKIE, expired)
    assert alice.get("/api/auth/me").status_code == 401

    assert alice.post("/api/auth/refresh").status_code == 200
    assert alice.get("/api/auth/me").status_code == 200


def test_access_token_signed_with_another_key_is_rejected(alice):
    forged = jwt.encode(
        {
            "sub": alice.user_id,
            "sid": "whatever",
            "type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        },
        "an-attacker-chosen-key",
        algorithm="HS256",
    )
    replace_cookie(alice.raw, ACCESS_COOKIE, forged)
    assert alice.get("/api/auth/me").status_code == 401


def test_refresh_token_cannot_be_used_as_an_access_token(alice):
    refresh = alice.raw.cookies.get(REFRESH_COOKIE)
    replace_cookie(alice.raw, ACCESS_COOKIE, refresh)
    assert alice.get("/api/auth/me").status_code == 401


def test_deactivated_account_loses_access(alice, db_session):
    user = db_session.query(User).filter(User.id == alice.user_id).first()
    user.is_active = False
    db_session.commit()
    assert alice.get("/api/auth/me").status_code == 401


# ── Password change ───────────────────────────────────────────────────────────

def test_password_change_requires_the_current_password(alice):
    response = alice.post(
        "/api/auth/password",
        json={"current_password": "NotMyPassword1", "new_password": "BrandNewPass9"},
    )
    assert response.status_code == 401


def test_password_change_rotates_the_session_and_invalidates_others(client, alice):
    from fastapi.testclient import TestClient

    from backend.main import app

    # A second browser logged into the same account.
    with TestClient(app, base_url="http://testserver") as second:
        login = second.post("/api/auth/login", json={"email": alice.email, "password": PASSWORD})
        assert login.status_code == 200

        changed = alice.post(
            "/api/auth/password",
            json={"current_password": PASSWORD, "new_password": "BrandNewPass9"},
        )
        assert changed.status_code == 200, changed.text

        # The other browser is signed out.
        assert second.get("/api/auth/me").status_code == 401

    # The browser that changed it keeps working, with the new password valid.
    assert alice.get("/api/auth/me").status_code == 200
    reset_all()
    fresh = client.post("/api/auth/login", json={"email": alice.email, "password": "BrandNewPass9"})
    assert fresh.status_code == 200
