from __future__ import annotations

from src.database.models import Recommendation
from src.database.repositories import RecommendationRepository, UserRepository
from src.database.session import session_scope
from src.services.errors import NotFoundError


def add_recommendation(
    *,
    login: str,
    text: str,
    database_url: str | None = None,
    echo_sql: bool = False,
) -> Recommendation:
    with session_scope(database_url=database_url, echo=echo_sql) as session:
        user_repo = UserRepository(session)
        user = user_repo.get_by_login(login)
        if user is None:
            raise NotFoundError(f"User with login '{login}' not found.")
        rec_repo = RecommendationRepository(session)
        return rec_repo.create(user_id=user.id, text=text)


def list_recommendations(
    *, login: str, database_url: str | None = None, echo_sql: bool = False
) -> list[Recommendation]:
    with session_scope(database_url=database_url, echo=echo_sql) as session:
        user_repo = UserRepository(session)
        user = user_repo.get_by_login(login)
        if user is None:
            raise NotFoundError(f"User with login '{login}' not found.")
        rec_repo = RecommendationRepository(session)
        return rec_repo.list_for_user(user_id=user.id)
