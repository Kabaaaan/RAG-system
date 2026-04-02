from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.database.models import Recommendation, RecommendationType


class RecommendationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        lead_id: int,
        recommendation_type: RecommendationType,
        text: str,
    ) -> Recommendation:
        recommendation = Recommendation(
            lead_id=lead_id,
            type=recommendation_type,
            text=text,
        )
        self._session.add(recommendation)
        self._session.flush()
        return recommendation

    def list_for_lead(self, *, lead_id: int, limit: int = 100) -> list[Recommendation]:
        statement: Select[tuple[Recommendation]] = (
            select(Recommendation)
            .where(Recommendation.lead_id == lead_id)
            .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())
