from __future__ import annotations

from pathlib import Path
from typing import Annotated

import click
from fastapi import APIRouter, Depends
from fastapi import status as http_status

from src.api.dependencies import RuntimeOptions, get_runtime_options
from src.api.schemas import CourseResponse, SeedCoursesRequest, SeedCoursesResponse
from src.cli.loaders import load_courses
from src.services import list_courses, seed_courses

router = APIRouter(prefix="/courses", tags=["courses"])
RuntimeOptionsDep = Annotated[RuntimeOptions, Depends(get_runtime_options)]


@router.post("/seed", response_model=SeedCoursesResponse)
def seed_courses_endpoint(
    payload: SeedCoursesRequest,
    options: RuntimeOptionsDep,
) -> SeedCoursesResponse:
    courses = load_courses(Path(payload.file_path))
    if not courses:
        raise click.ClickException("No courses found in the provided file.")

    created = seed_courses(courses, database_url=options.database_url, echo_sql=options.echo_sql)
    return SeedCoursesResponse(inserted=created)


@router.get("", response_model=list[CourseResponse], status_code=http_status.HTTP_200_OK)
def list_courses_endpoint(
    options: RuntimeOptionsDep,
) -> list[CourseResponse]:
    courses = list_courses(database_url=options.database_url, echo_sql=options.echo_sql)
    return [CourseResponse.model_validate(course) for course in courses]
