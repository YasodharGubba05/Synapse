"""Shared FastAPI dependencies: authentication, CSRF, rate limiting, ownership."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.database.models import AuthSession, MeetingSession, User
from backend.security.cookies import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER
from backend.security.ratelimit import check_rate_limit, client_ip
from backend.security.tokens import ACCESS_TOKEN_TYPE, decode_token

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Cookie"},
)


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite hands back naive datetimes; normalise to UTC-aware."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def verify_csrf(request: Request) -> None:
    """Double-submit CSRF check for state-changing requests."""
    if request.method in SAFE_METHODS:
        return
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get(CSRF_HEADER, "")
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Resolve the caller from the HTTP-only access cookie.

    Raises 401 when the token is absent, invalid, expired, or its server-side
    auth session has been revoked (logout), so a logged-out access token stops
    working immediately rather than when it would have expired.
    """
    token = request.cookies.get(ACCESS_COOKIE, "")
    claims = decode_token(token, ACCESS_TOKEN_TYPE)
    if not claims:
        raise _UNAUTHENTICATED

    auth_session = (
        db.query(AuthSession)
        .filter(AuthSession.id == claims["sid"], AuthSession.user_id == claims["sub"])
        .first()
    )
    now = datetime.now(timezone.utc)
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or (_aware(auth_session.expires_at) or now) <= now
    ):
        raise _UNAUTHENTICATED

    user = db.query(User).filter(User.id == claims["sub"]).first()
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED

    verify_csrf(request)

    check_rate_limit(
        f"api:{user.id}",
        settings.api_rate_limit,
        settings.api_rate_window_seconds,
    )

    request.state.user_id = user.id
    request.state.auth_session_id = auth_session.id
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


def rate_limit_ip(request: Request, bucket: str, limit: int, window_seconds: int) -> None:
    check_rate_limit(f"{bucket}:{client_ip(request)}", limit, window_seconds)


def require_owned_session(
    db: Session,
    user: User,
    session_id: str,
) -> MeetingSession:
    """Load a meeting session, enforcing that `user` owns it.

    404 when no such session exists, 403 when it exists but belongs to someone
    else. Every endpoint that accepts a session_id - in the path *or* in the
    request body - goes through here, which is what closes the IDOR hole.
    """
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id is required")

    meeting = db.query(MeetingSession).filter(MeetingSession.id == session_id).first()
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if meeting.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this meeting session",
        )
    return meeting
