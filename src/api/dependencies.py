from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query


@dataclass(slots=True, frozen=True)
class RuntimeOptions:
    database_url: str | None
    echo_sql: bool


def get_runtime_options(
    database_url: str | None = Query(
        default=None,
        description="Database URL override (otherwise uses POSTGRES_* settings).",
    ),
    echo_sql: bool = Query(default=False, description="Enable SQLAlchemy SQL echoing."),
) -> RuntimeOptions:
    return RuntimeOptions(database_url=database_url, echo_sql=echo_sql)
