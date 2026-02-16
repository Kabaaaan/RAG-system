from __future__ import annotations

from pathlib import Path
from typing import Annotated

import click
from fastapi import APIRouter, Depends, status

from src.api.dependencies import RuntimeOptions, get_runtime_options
from src.api.schemas import (
    CreateUserRequest,
    SeedUsersRequest,
    SeedUsersResponse,
    UserResponse,
)
from src.cli.loaders import load_users
from src.services import create_user, list_users, seed_users

router = APIRouter(prefix="/users", tags=["users"])
RuntimeOptionsDep = Annotated[RuntimeOptions, Depends(get_runtime_options)]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: CreateUserRequest,
    options: RuntimeOptionsDep,
) -> UserResponse:
    user = create_user(
        login=payload.login,
        digital_footprints=payload.digital_footprints,
        database_url=options.database_url,
        echo_sql=options.echo_sql,
    )
    response: UserResponse = UserResponse.model_validate(user)
    return response


@router.get("", response_model=list[UserResponse])
def list_users_endpoint(
    options: RuntimeOptionsDep,
) -> list[UserResponse]:
    users = list_users(database_url=options.database_url, echo_sql=options.echo_sql)
    return [UserResponse.model_validate(user) for user in users]


@router.post("/seed", response_model=SeedUsersResponse)
def seed_users_endpoint(
    payload: SeedUsersRequest,
    options: RuntimeOptionsDep,
) -> SeedUsersResponse:
    users = load_users(Path(payload.file_path))
    if not users:
        raise click.ClickException("No users found in the provided file.")

    stats = seed_users(users, database_url=options.database_url, echo_sql=options.echo_sql)
    return SeedUsersResponse(created=stats.created, updated=stats.updated, skipped=stats.skipped)
