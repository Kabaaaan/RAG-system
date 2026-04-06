from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class ResourceType(Base):
    __tablename__ = "resource_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    resources: Mapped[list[RAGResource]] = relationship(
        back_populates="resource_type",
        cascade="save-update, merge",
    )


class RAGResource(Base):
    __tablename__ = "rag_resources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    type_id: Mapped[int] = mapped_column(
        ForeignKey("resource_types.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    resource_type: Mapped[ResourceType] = relationship(back_populates="resources")


class RecommendationType(Base):
    __tablename__ = "recommendation_types"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="recommendation_type",
        cascade="save-update, merge",
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    type_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_types.id"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    recommendation_type: Mapped[RecommendationType] = relationship(back_populates="recommendations")
