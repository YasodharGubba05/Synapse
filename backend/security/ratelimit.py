"""In-process sliding-window rate limiter.

Deliberately dependency-free: Synapse's backend runs as a single Render web
service, so a per-process limiter is effective. Durable brute-force protection
does not rely on it alone - repeated login failures also lock the account row
in the database, which survives restarts and extra instances.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

_buckets: Dict[str, Deque[float]] = {}
_lock = threading.Lock()
_last_sweep = 0.0


def _sweep(now: float) -> None:
    global _last_sweep
    if now - _last_sweep < 300:
        return
    _last_sweep = now
    stale = [key for key, hits in _buckets.items() if not hits or now - hits[-1] > 3600]
    for key in stale:
        _buckets.pop(key, None)


def check_rate_limit(key: str, limit: int, window_seconds: int) -> int:
    """Register a hit. Returns remaining allowance; raises 429 when exceeded."""
    now = time.monotonic()
    with _lock:
        _sweep(now)
        hits = _buckets.setdefault(key, deque())
        cutoff = now - window_seconds
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(int(window_seconds - (now - hits[0])), 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        return limit - len(hits)


def reset_rate_limit(key: str) -> None:
    with _lock:
        _buckets.pop(key, None)


def reset_all() -> None:
    """Test helper."""
    with _lock:
        _buckets.clear()


def client_ip(request: Request) -> str:
    """Best-effort client IP behind Render's proxy."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"
