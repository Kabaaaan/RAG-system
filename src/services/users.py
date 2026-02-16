from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.database.models import User
from src.database.repositories import UserRepository
from src.database.session import session_scope
from src.services.errors import AlreadyExistsError, ValidationError


@dataclass(slots=True, frozen=True)
class SeedUsersStats:
    created: int
    updated: int
    skipped: int


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


def get_user_by_login(
    *,
    login: str,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> User | None:
    with session_scope(database_url=database_url, echo=echo_sql) as session:
        repo = UserRepository(session)
        return repo.get_by_login(login)


def seed_users(
    users: Sequence[Mapping[str, Any]],
    *,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> SeedUsersStats:
    if not users:
        raise ValidationError("No users provided.")

    created = 0
    updated = 0
    skipped = 0

    with session_scope(database_url=database_url, echo=echo_sql) as session:
        repo = UserRepository(session)
        for item in users:
            login = str(item.get("login") or "").strip()
            events = item.get("events")
            if not login or not isinstance(events, Sequence) or isinstance(events, str):
                skipped += 1
                continue

            digital_footprints = json.dumps({"events": list(events)}, ensure_ascii=False)
            existing_user = repo.get_by_login(login)
            if existing_user is None:
                repo.create(login=login, digital_footprints=digital_footprints)
                created += 1
                continue

            if existing_user.digital_footprints != digital_footprints:
                repo.update_digital_footprints(
                    user_id=existing_user.id,
                    digital_footprints=digital_footprints,
                )
                updated += 1
            else:
                skipped += 1

    return SeedUsersStats(created=created, updated=updated, skipped=skipped)
