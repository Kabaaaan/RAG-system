from __future__ import annotations

from pathlib import Path

import click

from src.cli.context import CLIContext
from src.cli.loaders import load_courses
from src.services import ServiceError, init_db, list_and_vectorize_courses, seed_courses


@click.command("init-db")
@click.option(
    "--drop-existing",
    is_flag=True,
    help="Drop existing tables before creating the schema.",
)
@click.option(
    "--courses-file",
    type=click.Path(path_type=Path),
    default=Path("data/courses.json"),
    show_default=True,
    help="Courses JSON file to seed before indexing into Qdrant.",
)
@click.option(
    "--skip-courses-seed",
    is_flag=True,
    help="Do not seed courses from file; only index courses already in DB.",
)
@click.pass_obj
def init_db_command(
    context: CLIContext,
    drop_existing: bool,
    courses_file: Path,
    skip_courses_seed: bool,
) -> None:
    try:
        init_db(
            database_url=context.database_url,
            echo_sql=context.echo_sql,
            drop_existing=drop_existing,
        )
        inserted = 0
        if not skip_courses_seed:
            courses = load_courses(courses_file)
            if not courses:
                raise click.ClickException("No courses found in the provided file.")
            inserted = seed_courses(
                courses,
                database_url=context.database_url,
                echo_sql=context.echo_sql,
            )

        stats = list_and_vectorize_courses(
            database_url=context.database_url,
            echo_sql=context.echo_sql,
            recreate_collection=drop_existing,
        )
    except ServiceError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surfacing database errors to CLI
        raise click.ClickException(str(exc)) from exc

    click.echo("Database schema initialized.")
    if not skip_courses_seed:
        click.echo(f"Courses seeded: {inserted} new item(s).")
    click.echo(
        "Qdrant indexing completed. "
        f"Courses: {stats.courses_count}, Chunks: {stats.chunks_count}, "
        f"Collection recreated: {'yes' if stats.collection_recreated else 'no'}."
    )
