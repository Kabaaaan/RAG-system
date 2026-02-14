from __future__ import annotations

from src.database.session import create_tables


def init_db(
    *,
    database_url: str | None = None,
    echo_sql: bool = False,
    drop_existing: bool = False,
) -> None:
    create_tables(database_url=database_url, echo=echo_sql, drop_existing=drop_existing)
