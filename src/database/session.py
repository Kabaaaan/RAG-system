from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base

if TYPE_CHECKING:
    from src.config.settings import AppSettings

_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker[Session] | None = None


def build_database_url(settings: AppSettings | None = None) -> str:
    env_database_url = os.getenv("DATABASE_URL", "").strip()
    if env_database_url:
        return env_database_url

    if settings is None:
        from src.config.settings import get_settings

        app_settings = get_settings()
    else:
        app_settings = settings
    host = app_settings.postgres_host.strip()
    database = app_settings.postgres_db.strip()
    user = app_settings.postgres_user.strip()
    password = app_settings.postgres_password.strip()
    port = app_settings.postgres_port

    if not all([host, database, user, password]):
        raise ValueError(
            "Database config is incomplete. Set DATABASE_URL or POSTGRES_HOST/PORT/DB/USER/PASSWORD."
        )

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def get_engine(*, database_url: str | None = None, echo: bool = False) -> Engine:
    global _ENGINE
    if database_url:
        return create_engine(database_url, echo=echo, pool_pre_ping=True)
    if _ENGINE is None:
        _ENGINE = create_engine(build_database_url(), echo=echo, pool_pre_ping=True)
    return _ENGINE


def get_session_factory(
    *,
    database_url: str | None = None,
    echo: bool = False,
) -> sessionmaker[Session]:
    global _SESSION_FACTORY
    if database_url:
        return sessionmaker(
            bind=get_engine(database_url=database_url, echo=echo),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(
            bind=get_engine(echo=echo),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _SESSION_FACTORY


@contextmanager
def session_scope(*, database_url: str | None = None, echo: bool = False) -> Iterator[Session]:
    session_factory = get_session_factory(database_url=database_url, echo=echo)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables(
    *, database_url: str | None = None, echo: bool = False, drop_existing: bool = False
) -> None:
    engine = get_engine(database_url=database_url, echo=echo)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
    if drop_existing:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def drop_tables(*, database_url: str | None = None, echo: bool = False) -> None:
    engine = get_engine(database_url=database_url, echo=echo)
    Base.metadata.drop_all(engine)


def dispose_engine() -> None:
    global _ENGINE, _SESSION_FACTORY
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _SESSION_FACTORY = None
