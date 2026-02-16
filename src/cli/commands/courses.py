from __future__ import annotations

from pathlib import Path

import click

from src.cli.context import CLIContext
from src.cli.loaders import load_courses
from src.cli.output import render_table
from src.services import ServiceError, ValidationError, list_courses, seed_courses


@click.command("seed-courses")
@click.option("--file", "file_path", type=click.Path(path_type=Path), required=True)
@click.pass_obj
def seed_courses_command(context: CLIContext, file_path: Path) -> None:
    courses = load_courses(file_path)
    if not courses:
        raise click.ClickException("No courses found in the provided file.")

    try:
        created = seed_courses(
            courses,
            database_url=context.database_url,
            echo_sql=context.echo_sql,
        )
    except ValidationError as exc:
        raise click.ClickException(str(exc)) from exc
    except ServiceError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surfacing database errors to CLI
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Inserted {created} new course(s).")


@click.command("show-courses")
@click.pass_obj
def show_courses_command(context: CLIContext) -> None:
    try:
        courses = list_courses(
            database_url=context.database_url,
            echo_sql=context.echo_sql,
        )
    except ServiceError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surfacing database errors to CLI
        raise click.ClickException(str(exc)) from exc

    if not courses:
        click.echo("No courses found.")
        return

    rows = [[str(course.id), course.name, course.description] for course in courses]
    click.echo(render_table(["ID", "Name", "Description"], rows))
