"""Environment-driven application configuration.

Every production-sensitive value (database, secret key, allowed origins,
cookie policy, rate limits) is read from the environment so that no
credential or deployment-specific value is hardcoded in the repository.
"""
from __future__ import annotations

import os
import secrets
from functools import lru_cache
from typing import List

try:  # Optional: load a local .env during development only.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _split_csv(raw: str) -> List[str]:
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


class Settings:
    """Immutable view over the process environment."""

    def __init__(self) -> None:
        self.environment: str = (_env("ENVIRONMENT", "development")).lower()
        self.is_production: bool = self.environment == "production"

        # ── Secrets ───────────────────────────────────────────────────────────
        secret = _env("SECRET_KEY")
        if not secret:
            if self.is_production:
                raise RuntimeError(
                    "SECRET_KEY is required when ENVIRONMENT=production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
            # Development fallback: ephemeral, so restarting invalidates tokens.
            secret = secrets.token_urlsafe(48)
        self.secret_key: str = secret
        self.jwt_algorithm: str = "HS256"

        # ── Database ──────────────────────────────────────────────────────────
        self.database_url: str = self._normalize_database_url(
            _env("DATABASE_URL") or "sqlite:///./synapse.db"
        )
        self.db_pool_size: int = _env_int("DB_POOL_SIZE", 5)
        self.db_max_overflow: int = _env_int("DB_MAX_OVERFLOW", 10)
        self.db_echo: bool = _env_bool("DB_ECHO", False)

        # ── Sessions / cookies ────────────────────────────────────────────────
        self.access_token_minutes: int = _env_int("ACCESS_TOKEN_MINUTES", 30)
        self.refresh_token_days: int = _env_int("REFRESH_TOKEN_DAYS", 14)
        self.cookie_domain: str = _env("COOKIE_DOMAIN") or ""
        # Cross-site cookies (Vercel frontend -> Render backend) require
        # SameSite=None + Secure. Same-origin/dev setups use Lax over http.
        default_samesite = "none" if self.is_production else "lax"
        self.cookie_samesite: str = (_env("COOKIE_SAMESITE", default_samesite)).lower()
        self.cookie_secure: bool = _env_bool("COOKIE_SECURE", self.is_production)
        if self.cookie_samesite == "none":
            # Browsers reject SameSite=None without Secure.
            self.cookie_secure = True

        # ── CORS ──────────────────────────────────────────────────────────────
        origins = _split_csv(_env("ALLOWED_ORIGINS"))
        frontend = _env("FRONTEND_URL").rstrip("/")
        if frontend and frontend not in origins:
            origins.append(frontend)
        if not origins and not self.is_production:
            origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
            ]
        self.allowed_origins: List[str] = origins
        self.allowed_origin_regex: str = _env("ALLOWED_ORIGIN_REGEX") or ""

        # ── Limits ────────────────────────────────────────────────────────────
        self.max_upload_bytes: int = _env_int("MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
        self.max_json_body_bytes: int = _env_int("MAX_JSON_BODY_BYTES", 1024 * 1024)
        self.login_rate_limit: int = _env_int("LOGIN_RATE_LIMIT", 10)
        self.login_rate_window_seconds: int = _env_int("LOGIN_RATE_WINDOW_SECONDS", 900)
        self.register_rate_limit: int = _env_int("REGISTER_RATE_LIMIT", 5)
        self.register_rate_window_seconds: int = _env_int("REGISTER_RATE_WINDOW_SECONDS", 3600)
        self.api_rate_limit: int = _env_int("API_RATE_LIMIT", 240)
        self.api_rate_window_seconds: int = _env_int("API_RATE_WINDOW_SECONDS", 60)
        self.max_failed_logins: int = _env_int("MAX_FAILED_LOGINS", 8)
        self.account_lock_minutes: int = _env_int("ACCOUNT_LOCK_MINUTES", 15)

        # ── Misc ──────────────────────────────────────────────────────────────
        self.enable_docs: bool = _env_bool("ENABLE_DOCS", not self.is_production)
        self.auto_create_tables: bool = _env_bool("AUTO_CREATE_TABLES", not self.is_production)
        self.run_migrations_on_startup: bool = _env_bool("RUN_MIGRATIONS_ON_STARTUP", self.is_production)
        self.trusted_hosts: List[str] = _split_csv(_env("TRUSTED_HOSTS")) or ["*"]

    @staticmethod
    def _normalize_database_url(url: str) -> str:
        """Render/Heroku hand out postgres:// URLs; SQLAlchemy needs a driver."""
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def configuration_warnings(self) -> List[str]:
        """Deployment mistakes that leave the app running but unusable.

        These are the failures that are hardest to diagnose from the
        outside - the service is "up", the health check is green, and every
        browser request still fails. Surfacing them at startup and on the
        health endpoint turns a confusing outage into a one-line answer.
        """
        problems: List[str] = []

        if self.cookie_samesite not in {"lax", "strict", "none"}:
            problems.append(
                f"COOKIE_SAMESITE={self.cookie_samesite!r} is not one of lax/strict/none; "
                "browsers will reject the session cookies."
            )

        if not self.is_production:
            return problems

        if not self.allowed_origins and not self.allowed_origin_regex:
            problems.append(
                "ALLOWED_ORIGINS (or FRONTEND_URL) is not set. CORS will reject every "
                "browser request, so login will fail with a network error. Set it to the "
                "deployed frontend origin, e.g. https://your-app.vercel.app"
            )

        if self.is_sqlite:
            problems.append(
                "DATABASE_URL is SQLite in production. On a container host with an "
                "ephemeral filesystem every deploy and restart erases all accounts and "
                "meetings. Point DATABASE_URL at managed PostgreSQL."
            )

        if self.cookie_samesite == "none" and not self.cookie_secure:
            problems.append("SameSite=None requires Secure; cookies would be dropped.")

        if not self.cookie_secure:
            problems.append(
                "COOKIE_SECURE is off in production; session cookies would travel over plain HTTP."
            )

        if self.enable_docs:
            problems.append("ENABLE_DOCS is on in production; the API schema is publicly browsable.")

        return problems


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
