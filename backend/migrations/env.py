"""Alembic environment: resolves the database URL from the app settings."""
from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.config import settings  # noqa: E402
from backend.database.connection import Base  # noqa: E402
from backend.database import models  # noqa: E402,F401  (registers the models)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

# When Alembic is driven from the command line it should set logging up from
# alembic.ini. When it is called from inside the running app (startup
# migrations), it must NOT: fileConfig() disables every existing logger by
# default, which would silence the application and uvicorn access logs for
# the rest of the process's life.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
