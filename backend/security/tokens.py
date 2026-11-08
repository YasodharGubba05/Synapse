"""Signed access/refresh token issuing and verification (JWT, HS256)."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

from backend.config import settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, auth_session_id: str) -> tuple[str, datetime]:
    expires_at = _now() + timedelta(minutes=settings.access_token_minutes)
    token = _encode(
        {
            "sub": user_id,
            "sid": auth_session_id,
            "type": ACCESS_TOKEN_TYPE,
            "iat": int(_now().timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": uuid.uuid4().hex,
        }
    )
    return token, expires_at


def create_refresh_token(user_id: str, auth_session_id: str) -> tuple[str, datetime]:
    expires_at = _now() + timedelta(days=settings.refresh_token_days)
    token = _encode(
        {
            "sub": user_id,
            "sid": auth_session_id,
            "type": REFRESH_TOKEN_TYPE,
            "iat": int(_now().timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": uuid.uuid4().hex,
        }
    )
    return token, expires_at


def decode_token(token: str, expected_type: str) -> Optional[dict[str, Any]]:
    """Return the token claims, or None if the token is invalid/expired/wrong type."""
    if not token:
        return None
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if claims.get("type") != expected_type:
        return None
    if not claims.get("sub") or not claims.get("sid"):
        return None
    return claims


def hash_refresh_token(token: str) -> str:
    """Refresh tokens are stored only as a SHA-256 digest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
