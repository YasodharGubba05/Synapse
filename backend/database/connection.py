"""SQLAlchemy engine/session wiring.

The database target is environment driven:
  * local development  -> sqlite:///./synapse.db   (default)
  * production         -> DATABASE_URL pointing at managed PostgreSQL
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import settings

DATABASE_URL = settings.database_url

if settings.is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.db_echo,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=1800,
        echo=settings.db_echo,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    from backend.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
