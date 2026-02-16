from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    updated_at: datetime


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    created_at: datetime


class CreateUserRequest(BaseModel):
    login: str
    digital_footprints: str = ""


class SeedUsersRequest(BaseModel):
    file_path: str = "data/digital-footprints.json"


class SeedUsersResponse(BaseModel):
    created: int
    updated: int
    skipped: int


class SeedCoursesRequest(BaseModel):
    file_path: str


class SeedCoursesResponse(BaseModel):
    inserted: int


class AddRecommendationRequest(BaseModel):
    login: str
    text: str


class RetrievedCourseResponse(BaseModel):
    course_id: int
    name: str
    description: str
    score: float


class GenerateRecommendationRequest(BaseModel):
    login: str
    top_k: int = Field(default=5, ge=1, le=20)
    search_k: int = Field(default=20, ge=1, le=100)


class GenerateRecommendationResponse(BaseModel):
    recommendation: RecommendationResponse
    debug_file_path: str
    query_text: str
    retrieved_courses: list[RetrievedCourseResponse]


class InitDbRequest(BaseModel):
    drop_existing: bool = False
    courses_file: str = "data/courses.json"
    skip_courses_seed: bool = False


class InitDbResponse(BaseModel):
    courses_seeded: int
    courses_count: int
    chunks_count: int
    collection_recreated: bool
