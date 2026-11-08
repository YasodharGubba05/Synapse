"""Single entry point for applying Alembic migrations.

Both the application's startup hook and the `backend.cli migrate` command go
through here, so the advisory lock below protects every path. Without it, two
processes starting at the same moment against an empty PostgreSQL database
race on CREATE TABLE and one of them dies with a `pg_type_typname_nsp_index`
unique violation.
"""
from __future__ import annotations

import logging
from pathlib import Path

from backend.config import settings

logger = logging.getLogger(__name__)

# Arbitrary but fixed: every Synapse process uses the same key, so only one of
# them holds the migration lock at a time.
MIGRATION_LOCK_KEY = 8_314_427_001


def _alembic_config():
    from alembic.config import Config

    root = Path(__file__).resolve().parent
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    # Leave the application's logging configuration alone; Alembic's
    # fileConfig() would otherwise disable every existing logger.
    cfg.attributes["configure_logger"] = False
    return cfg


def run_migrations() -> None:
    """Upgrade the database to head, serialised across processes."""
    from alembic import command
    from sqlalchemy import text

    from backend.database.connection import engine

    cfg = _alembic_config()

    if settings.is_sqlite:
        # SQLite deployments are single-process by nature.
        command.upgrade(cfg, "head")
        return

    with engine.connect() as lock_conn:
        logger.info("Acquiring migration lock…")
        lock_conn.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK_KEY})
        lock_conn.commit()
        try:
            command.upgrade(cfg, "head")
        finally:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK_KEY})
            lock_conn.commit()
