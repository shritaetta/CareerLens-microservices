import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

try:
    from models import Base
except ImportError:
    from .models import Base


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    # Normalize postgres URL to use SQLAlchemy 2.x psycopg driver
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_database_url()
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _session_factory


def init_db():
    """Initializes tables at startup."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def close_db():
    """Disposes engine pool on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _session_factory = None


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
