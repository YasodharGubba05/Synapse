"""Cookie names and the single place cookie policy is applied."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Response

from backend.config import settings

ACCESS_COOKIE = "synapse_access"
REFRESH_COOKIE = "synapse_refresh"
CSRF_COOKIE = "synapse_csrf"
CSRF_HEADER = "X-CSRF-Token"


def _max_age(expires_at: datetime) -> int:
    delta = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    return max(delta, 1)


def _common_kwargs() -> dict:
    kwargs = {
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    return kwargs


def _mark_partitioned(response: Response) -> None:
    """Add the CHIPS `Partitioned` attribute to cross-site cookies.

    When the frontend and API sit on different registrable domains the
    session cookies are third-party. Browsers that restrict or partition
    third-party cookies keep a `Partitioned` cookie working, scoped to the
    top-level site. Browsers that do not know the attribute ignore it, so
    this is safe to always send in SameSite=None mode.
    """
    if settings.cookie_samesite != "none":
        return
    # Mutate in place: Starlette caches a MutableHeaders view over this very
    # list, so rebinding the attribute would be silently discarded.
    for index, (key, value) in enumerate(response.raw_headers):
        if key.lower() == b"set-cookie" and b"Partitioned" not in value:
            response.raw_headers[index] = (key, value + b"; Partitioned")


def set_auth_cookies(
    response: Response,
    access_token: str,
    access_expires_at: datetime,
    refresh_token: str,
    refresh_expires_at: datetime,
    csrf_token: str,
) -> None:
    common = _common_kwargs()
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        max_age=_max_age(access_expires_at),
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        max_age=_max_age(refresh_expires_at),
        **common,
    )
    # Readable by JS on purpose: the client echoes it back in X-CSRF-Token
    # (double-submit pattern). It is not a credential on its own.
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        max_age=_max_age(refresh_expires_at),
        **common,
    )
    _mark_partitioned(response)


def clear_auth_cookies(response: Response) -> None:
    common = _common_kwargs()
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, **common)
    # The deletion must carry the same attributes as the cookie it clears.
    _mark_partitioned(response)
