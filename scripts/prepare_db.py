from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg2

from src.database.session import build_database_url
from src.services.db import init_db

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

REFERENCE_DATA_SQL = ROOT_DIR / "data" / "reference_data_seed.sql"
REBUILD_SCHEMA_SQL = ROOT_DIR / "migrations" / "20260406_01_rebuild_rag_schema.sql"


def _postgres_dsn() -> str:
    return build_database_url().replace("+psycopg2", "")


def _execute_sql_file(path: Path) -> None:
    sql = path.read_text(encoding="utf-8")

    if "-- Down" in sql:
        sql = sql.split("-- Down")[0].strip()

    with psycopg2.connect(_postgres_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()


def init_schema() -> None:
    init_db()
    _execute_sql_file(REFERENCE_DATA_SQL)


def rebuild_schema() -> None:
    _execute_sql_file(REBUILD_SCHEMA_SQL)
    _execute_sql_file(REFERENCE_DATA_SQL)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare PostgreSQL schema and static reference data for the RAG system."
    )
    parser.add_argument(
        "--mode",
        choices=("init", "rebuild"),
        default="init",
        help=(
            "'init' creates missing tables and seeds reference data. "
            "'rebuild' applies the destructive schema rebuild migration and then seeds reference data."
        ),
    )
    args = parser.parse_args()

    if args.mode == "rebuild":
        rebuild_schema()
        print("Schema rebuilt and reference data seeded.")
        return

    init_schema()
    print("Schema initialized and reference data seeded.")


if __name__ == "__main__":
    main()
