from __future__ import annotations

from pathlib import Path

import click

from src.cli.context import CLIContext
from src.cli.loaders import load_users
from src.cli.output import render_table
from src.services import AlreadyExistsError, ServiceError, create_user, list_users, seed_users


@click.command("create-user")
@click.option("--login", required=True)
@click.option("--digital-footprints", default="", help="JSON or text describing user activity.")
@click.pass_obj
def create_user_command(context: CLIContext, login: str, digital_footprints: str) -> None:
    try:
        user = create_user(
            login=login,
            digital_footprints=digital_footprints,
            database_url=context.database_url,
            echo_sql=context.echo_sql,
        )
    except AlreadyExistsError as exc:
        raise click.ClickException(str(exc)) from exc
    except ServiceError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surfacing database errors to CLI
        raise click.ClickException(str(exc)) from exc

    click.echo(f"User created with id={user.id}.")


@click.command("show-users")
@click.pass_obj
def show_users_command(context: CLIContext) -> None:
    try:
        users = list_users(
            database_url=context.database_url,
            echo_sql=context.echo_sql,
        )
    except ServiceError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surfacing database errors to CLI
        raise click.ClickException(str(exc)) from exc

    if not users:
        click.echo("No users found.")
        return

    rows = [[str(user.id), user.login, str(user.updated_at)] for user in users]
    click.echo(render_table(["ID", "Login", "Updated At"], rows))


@click.command("seed-users")
@click.option(
    "--file",
    "file_path",
    type=click.Path(path_type=Path),
    default=Path("data/digital-footprints.json"),
    show_default=True,
)
@click.pass_obj
def seed_users_command(context: CLIContext, file_path: Path) -> None:
    users = load_users(file_path)
    if not users:
        raise click.ClickException("No users found in the provided file.")

    try:
        stats = seed_users(
            users,
            database_url=context.database_url,
            echo_sql=context.echo_sql,
        )
    except ServiceError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surfacing service errors to CLI
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Users seeded. Created: {stats.created}, Updated: {stats.updated}, Skipped: {stats.skipped}.")
