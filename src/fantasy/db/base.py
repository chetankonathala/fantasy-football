"""SQLAlchemy engine, Base, and session factory.

Supports two modes:
- Local dev / SQLite: set DATABASE_PATH (or defaults to data/fantasy.db)
- Production / PostgreSQL: set DATABASE_URL (takes precedence, must be postgresql:// scheme)

Render injects DATABASE_URL automatically when a Postgres instance is linked.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _build_database_url() -> str:
    """Return the database connection URL, preferring DATABASE_URL over SQLite fallback."""
    database_url = os.environ.get("DATABASE_URL", "")

    if database_url:
        # Render supplies postgres:// (legacy) — SQLAlchemy 2.x requires postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    # Local dev fallback: SQLite
    db_path = Path(os.environ.get("DATABASE_PATH", str(PROJECT_ROOT / "data" / "fantasy.db")))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


DATABASE_URL = _build_database_url()
IS_POSTGRES = DATABASE_URL.startswith("postgresql")


class Base(DeclarativeBase):
    pass


def get_engine(url: str = DATABASE_URL):
    kwargs: dict = {"echo": False}
    if not IS_POSTGRES:
        # SQLite-specific: allow cross-thread usage in tests / dev
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)
