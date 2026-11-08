"""Registration, login, logout, session refresh and account introspection.

Architecture: short-lived access JWT + long-lived rotating refresh JWT, both
delivered as HTTP-only cookies, plus a readable CSRF cookie that the client
echoes back in X-CSRF-Token (double-submit). Every access token names a
server-side `auth_sessions` row, so logout revokes it immediately.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import crud
from backend.database.connection import get_db
from backend.database.models import User
from backend.dependencies import get_current_user, verify_csrf
from backend.models.schemas import (
    AuthResponse,
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    UserResponse,
)
from backend.security.cookies import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    clear_auth_cookies,
    set_auth_cookies,
)
from backend.security.passwords import dummy_verify, hash_password, needs_rehash, verify_password
from backend.security.ratelimit import check_rate_limit, client_ip, reset_rate_limit
from backend.security.tokens import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    hash_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect email or password",
)


def _aware(value):
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _serialize_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


def _issue_session(
    response: Response,
    request: Request,
    db: Session,
    user: User,
) -> AuthResponse:
    """Create a fresh auth session and attach all three cookies."""
    refresh_token, refresh_expires = create_refresh_token(user.id, "pending")
    auth_session = crud.create_auth_session(
        db,
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=refresh_expires,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
    )
    # Re-mint the refresh token now that the auth session id exists so the
    # `sid` claim and the stored hash describe the same row.
    refresh_token, refresh_expires = create_refresh_token(user.id, auth_session.id)
    crud.rotate_auth_session(db, auth_session, hash_refresh_token(refresh_token), refresh_expires)

    access_token, access_expires = create_access_token(user.id, auth_session.id)
    set_auth_cookies(
        response,
        access_token=access_token,
        access_expires_at=access_expires,
        refresh_token=refresh_token,
        refresh_expires_at=refresh_expires,
        csrf_token=generate_csrf_token(),
    )
    return AuthResponse(
        user=_serialize_user(user),
        expires_in=settings.access_token_minutes * 60,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    check_rate_limit(
        f"register:{client_ip(request)}",
        settings.register_rate_limit,
        settings.register_rate_window_seconds,
    )

    email = crud.normalize_email(body.email)
    if crud.get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    try:
        user = crud.create_user(
            db,
            email=email,
            password_hash=hash_password(body.password),
            full_name=body.full_name,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    logger.info("New account registered: user_id=%s", user.id)
    return _issue_session(response, request, db, user)


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ip = client_ip(request)
    email = crud.normalize_email(body.email)
    # Two buckets: one per source IP, one per IP+account, so a single account
    # cannot be ground down and a single host cannot spray many accounts.
    check_rate_limit(f"login-ip:{ip}", settings.login_rate_limit * 3, settings.login_rate_window_seconds)
    check_rate_limit(f"login:{ip}:{email}", settings.login_rate_limit, settings.login_rate_window_seconds)

    user = crud.get_user_by_email(db, email)
    if user is None:
        dummy_verify()  # keep response time comparable to a real check
        raise INVALID_CREDENTIALS

    locked_until = _aware(user.locked_until)
    if locked_until and locked_until > datetime.now(timezone.utc):
        retry_after = int((locked_until - datetime.now(timezone.utc)).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. This account is temporarily locked.",
            headers={"Retry-After": str(max(retry_after, 1))},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled")

    if not verify_password(body.password, user.password_hash):
        crud.record_failed_login(db, user, settings.max_failed_logins, settings.account_lock_minutes)
        raise INVALID_CREDENTIALS

    if needs_rehash(user.password_hash):
        crud.update_password_hash(db, user, hash_password(body.password))

    crud.record_successful_login(db, user)
    reset_rate_limit(f"login:{ip}:{email}")
    logger.info("Login succeeded: user_id=%s", user.id)
    return _issue_session(response, request, db, user)


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    verify_csrf(request)
    token = request.cookies.get(REFRESH_COOKIE, "")
    claims = decode_token(token, REFRESH_TOKEN_TYPE)
    if not claims:
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    auth_session = crud.get_auth_session(db, claims["sid"])
    now = datetime.now(timezone.utc)
    if (
        auth_session is None
        or auth_session.user_id != claims["sub"]
        or (_aware(auth_session.expires_at) or now) <= now
    ):
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    if auth_session.revoked_at is not None:
        # A revoked refresh token being replayed means it leaked: drop every
        # session this account has so the attacker and the user both stop.
        crud.revoke_all_auth_sessions(db, auth_session.user_id)
        clear_auth_cookies(response)
        logger.warning("Refresh token reuse detected for user_id=%s", auth_session.user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    if hash_refresh_token(token) != auth_session.refresh_token_hash:
        crud.revoke_all_auth_sessions(db, auth_session.user_id)
        clear_auth_cookies(response)
        logger.warning("Stale refresh token presented for user_id=%s", auth_session.user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user = crud.get_user_by_id(db, auth_session.user_id)
    if user is None or not user.is_active:
        crud.revoke_auth_session(db, auth_session)
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    new_refresh, refresh_expires = create_refresh_token(user.id, auth_session.id)
    crud.rotate_auth_session(db, auth_session, hash_refresh_token(new_refresh), refresh_expires)
    access_token, access_expires = create_access_token(user.id, auth_session.id)
    set_auth_cookies(
        response,
        access_token=access_token,
        access_expires_at=access_expires,
        refresh_token=new_refresh,
        refresh_expires_at=refresh_expires,
        csrf_token=generate_csrf_token(),
    )
    return AuthResponse(user=_serialize_user(user), expires_in=settings.access_token_minutes * 60)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    has_cookies = bool(request.cookies.get(ACCESS_COOKIE) or request.cookies.get(REFRESH_COOKIE))
    if has_cookies:
        verify_csrf(request)

    for cookie_name, token_type in ((REFRESH_COOKIE, REFRESH_TOKEN_TYPE),):
        claims = decode_token(request.cookies.get(cookie_name, ""), token_type)
        if claims:
            auth_session = crud.get_auth_session(db, claims["sid"])
            if auth_session is not None and auth_session.user_id == claims["sub"]:
                crud.revoke_auth_session(db, auth_session)

    # Also honour a still-valid access cookie whose refresh cookie was dropped.
    from backend.security.tokens import ACCESS_TOKEN_TYPE

    access_claims = decode_token(request.cookies.get(ACCESS_COOKIE, ""), ACCESS_TOKEN_TYPE)
    if access_claims:
        auth_session = crud.get_auth_session(db, access_claims["sid"])
        if auth_session is not None and auth_session.user_id == access_claims["sub"]:
            crud.revoke_auth_session(db, auth_session)

    clear_auth_cookies(response)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _serialize_user(user)


@router.post("/password", status_code=status.HTTP_200_OK)
def change_password(
    body: PasswordChangeRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current password",
        )

    crud.update_password_hash(db, user, hash_password(body.new_password))
    # Changing a password signs every device out, including this one.
    crud.revoke_all_auth_sessions(db, user.id)
    _issue_session(response, request, db, user)
    return {"detail": "Password updated"}
