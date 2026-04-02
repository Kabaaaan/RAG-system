from __future__ import annotations

import click

from src.cli.context import CLIContext
from src.services import ServiceError, init_db


@click.command("init-db")
@click.option(
    "--drop-existing",
    is_flag=True,
    help="Drop existing tables before creating the schema.",
)
@click.pass_obj
def init_db_command(
    context: CLIContext,
    drop_existing: bool,
) -> None:
    try:
        init_db(drop_existing=drop_existing)
    except ServiceError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surfacing database errors to CLI
        raise click.ClickException(str(exc)) from exc

    click.echo("Database schema initialized.")
