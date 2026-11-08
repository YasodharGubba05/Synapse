from pathlib import Path
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.db_migrate import run_migrations
from backend.routers import (
    auth, chat, meeting, models, suggestions, transcribe, history, intelligence,
)
from backend.services.groq_client import close_http_client, get_http_client
from backend.database.connection import create_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("synapse")


def _log_configuration_warnings() -> None:
    """Shout about deployment mistakes that leave the app up but unusable."""
    problems = settings.configuration_warnings()
    if not problems:
        logger.info("Configuration check passed (environment=%s)", settings.environment)
        return
    logger.error("=" * 72)
    logger.error("CONFIGURATION PROBLEMS DETECTED - the app will start but may not work:")
    for problem in problems:
        logger.error("  * %s", problem)
    logger.error("=" * 72)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _log_configuration_warnings()
    if settings.run_migrations_on_startup:
        try:
            run_migrations()
            logger.info("Database migrations applied")
        except Exception:
            logger.exception("Database migration failed")
            raise
    elif settings.auto_create_tables:
        create_tables()
    await get_http_client()
    try:
        yield
    finally:
        await close_http_client()


app = FastAPI(
    title="Synapse - Live Audio Intelligence",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

if settings.trusted_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

# Credentialed cookie auth requires an explicit origin allowlist - "*" is
# rejected by browsers when credentials are included, and is unsafe besides.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex or None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Groq-API-Key", "X-CSRF-Token", "Accept"],
    expose_headers=["Retry-After"],
    max_age=600,
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    # This service only ever returns JSON / SSE, never HTML that should run code.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
}
DOC_PATHS = {"/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Reject oversized JSON bodies early and attach security headers."""
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        size = int(content_length)
        is_upload = "multipart/form-data" in (request.headers.get("content-type") or "")
        cap = settings.max_upload_bytes if is_upload else settings.max_json_body_bytes
        if size > cap:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large"},
            )

    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        # Swagger UI needs to load its own scripts and styles.
        if header == "Content-Security-Policy" and request.url.path in DOC_PATHS:
            continue
        response.headers.setdefault(header, value)
    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    """Return field-level validation messages without echoing submitted values.

    The default handler includes the offending input, which would place
    passwords and Groq API keys into error responses and client logs.
    """
    errors = [
        {"field": ".".join(str(part) for part in err.get("loc", [])[1:]) or "body",
         "message": err.get("msg", "Invalid value")}
        for err in exc.errors()
    ]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak stack traces or internal detail to callers."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Mounted twice so both /api/... (through the Vercel/Vite proxy) and bare
# paths keep working, exactly as before.
for router in [
    auth.router, transcribe.router, suggestions.router, chat.router,
    meeting.router, history.router, intelligence.router, models.router,
]:
    app.include_router(router, prefix="/api")
    app.include_router(router)


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "app": "Synapse", "docs": "/docs" if settings.enable_docs else None}


@app.get("/api/health", tags=["health"])
async def api_health():
    return {"status": "ok"}


@app.get("/healthz", tags=["health"])
async def healthz():
    """Deployment health check - no database or third-party dependency.

    Deliberately does not touch the database: a slow or briefly unavailable
    database should not fail the deploy's health check and trigger a
    rollback loop. Database reachability is reported separately below.
    """
    payload = {"status": "ok", "environment": settings.environment}
    problems = settings.configuration_warnings()
    if problems:
        payload["configuration_warnings"] = problems
    return payload


@app.get("/readyz", tags=["health"])
async def readyz():
    """Readiness probe: confirms the database is actually reachable."""
    from sqlalchemy import text

    from backend.database.connection import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed: database unreachable")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "database": "unreachable"},
        )
    return {"status": "ok", "database": "reachable"}


if settings.enable_docs:
    @app.get("/api/docs", include_in_schema=False)
    async def api_docs_redirect():
        return RedirectResponse(url="/docs", status_code=307)

    @app.get("/api/openapi.json", include_in_schema=False)
    async def api_openapi_redirect():
        return RedirectResponse(url="/openapi.json", status_code=307)
