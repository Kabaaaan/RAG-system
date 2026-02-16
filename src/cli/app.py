from __future__ import annotations

import click

from src.cli.commands import ALL_COMMANDS
from src.cli.context import CLIContext
from src.config.settings import get_settings
from src.utils import configure_logging


@click.group()
@click.option(
    "--database-url",
    envvar="DATABASE_URL",
    default=None,
    help="Database URL override (otherwise uses POSTGRES_* settings).",
)
@click.option("--echo-sql", is_flag=True, help="Enable SQLAlchemy SQL echoing.")
@click.pass_context
def cli(context: click.Context, database_url: str | None, echo_sql: bool) -> None:
    configure_logging(get_settings().log_level)
    context.obj = CLIContext(database_url=database_url, echo_sql=echo_sql)


for command in ALL_COMMANDS:
    cli.add_command(command)
