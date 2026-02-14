from __future__ import annotations

from src.database.models import User
from src.database.repositories import UserRepository
from src.database.session import session_scope
from src.services.errors import AlreadyExistsError


def create_user(
    *,
    login: str,
    digital_footprints: str = "",
    database_url: str | None = None,
    echo_sql: bool = False,
) -> User:
    with session_scope(database_url=database_url, echo=echo_sql) as session:
        repo = UserRepository(session)
        if repo.get_by_login(login) is not None:
            raise AlreadyExistsError(f"User with login '{login}' already exists.")
        return repo.create(login=login, digital_footprints=digital_footprints)


def list_users(*, database_url: str | None = None, echo_sql: bool = False) -> list[User]:
    with session_scope(database_url=database_url, echo=echo_sql) as session:
        repo = UserRepository(session)
        return repo.list()
