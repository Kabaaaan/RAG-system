from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from qdrant_client import AsyncQdrantClient
from qdrant_client.conversions.common_types import CountResult
from qdrant_client.http.models.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    Record,
    ScoredPoint,
    UpdateResult,
    VectorParams,
)

from src.config.settings import AppSettings, get_settings

PointId = int | str
Vector = Sequence[float]
Payload = Mapping[str, Any]


@dataclass(slots=True, frozen=True)
class PointData:
    point_id: PointId
    vector: Vector
    payload: Payload | None = None


class QdrantVectorClient:
    """Async interface for Qdrant operations used by the RAG pipeline."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        *,
        settings: AppSettings | None = None,
        collection_name: str | None = None,
        api_key: str | None = None,
        https: bool = False,
        grpc_port: int = 6334,
        prefer_grpc: bool = False,
        timeout: int | None = 10,
    ) -> None:
        self._settings = settings or get_settings()
        self._default_collection_name = (collection_name or self._settings.qdrant_collection).strip() or None

        self._client = AsyncQdrantClient(
            host=host or self._settings.qdrant_host,
            port=port or self._settings.qdrant_port,
            api_key=api_key,
            https=https,
            grpc_port=grpc_port,
            prefer_grpc=prefer_grpc,
            timeout=timeout,
        )

    @classmethod
    async def connect(
        cls,
        host: str | None = None,
        port: int | None = None,
        *,
        settings: AppSettings | None = None,
        collection_name: str | None = None,
        api_key: str | None = None,
        https: bool = False,
        grpc_port: int = 6334,
        prefer_grpc: bool = False,
        timeout: int | None = 10,
    ) -> QdrantVectorClient:
        instance = cls(
            host=host,
            port=port,
            settings=settings,
            collection_name=collection_name,
            api_key=api_key,
            https=https,
            grpc_port=grpc_port,
            prefer_grpc=prefer_grpc,
            timeout=timeout,
        )
        await instance.healthcheck()
        return instance

    async def __aenter__(self) -> QdrantVectorClient:
        await self.healthcheck()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.close()

    async def healthcheck(self) -> None:
        await self._client.get_collections()

    def _resolve_collection_name(self, collection_name: str | None) -> str:
        resolved_collection = (collection_name or self._default_collection_name or "").strip()
        if not resolved_collection:
            raise ValueError("Qdrant collection name is not set. Configure QDRANT_COLLECTION or pass collection_name.")
        return resolved_collection

    async def collection_exists(self, collection_name: str | None = None) -> bool:
        resolved_collection = self._resolve_collection_name(collection_name)
        result = await self._client.collection_exists(collection_name=resolved_collection)
        return cast(bool, result)

    async def create_collection(
        self,
        vector_size: int,
        *,
        collection_name: str | None = None,
        distance: Distance = Distance.COSINE,
        on_disk_payload: bool = True,
        recreate_if_exists: bool = False,
    ) -> bool:
        resolved_collection = self._resolve_collection_name(collection_name)
        exists = await self.collection_exists(resolved_collection)
        if exists and not recreate_if_exists:
            return False

        if exists and recreate_if_exists:
            await self._client.delete_collection(collection_name=resolved_collection)

        result = await self._client.create_collection(
            collection_name=resolved_collection,
            vectors_config=VectorParams(size=vector_size, distance=distance),
            on_disk_payload=on_disk_payload,
        )
        return cast(bool, result)

    async def delete_collection(self, collection_name: str | None = None) -> bool:
        resolved_collection = self._resolve_collection_name(collection_name)
        result = await self._client.delete_collection(collection_name=resolved_collection)
        return cast(bool, result)

    async def add_point(
        self,
        point_id: PointId,
        vector: Vector,
        payload: Payload | None = None,
        *,
        collection_name: str | None = None,
        wait: bool = True,
    ) -> UpdateResult:
        resolved_collection = self._resolve_collection_name(collection_name)
        point = PointStruct(id=point_id, vector=list(vector), payload=dict(payload or {}))
        return await self._client.upsert(collection_name=resolved_collection, points=[point], wait=wait)

    async def add_points(
        self,
        points: Sequence[PointData],
        *,
        collection_name: str | None = None,
        wait: bool = True,
    ) -> UpdateResult:
        resolved_collection = self._resolve_collection_name(collection_name)
        qdrant_points = [
            PointStruct(id=item.point_id, vector=list(item.vector), payload=dict(item.payload or {})) for item in points
        ]
        return await self._client.upsert(collection_name=resolved_collection, points=qdrant_points, wait=wait)

    async def search(
        self,
        query_vector: Vector,
        k: int = 5,
        *,
        collection_name: str | None = None,
        score_threshold: float | None = None,
        with_payload: bool | Sequence[str] = True,
        with_vectors: bool | Sequence[str] = False,
    ) -> list[ScoredPoint]:
        resolved_collection = self._resolve_collection_name(collection_name)
        response = await self._client.query_points(
            collection_name=resolved_collection,
            query=list(query_vector),
            limit=k,
            score_threshold=score_threshold,
            with_payload=with_payload,
            with_vectors=with_vectors,
        )
        return cast(list[ScoredPoint], response.points)

    async def search_with_filter(
        self,
        query_vector: Vector,
        query_filter: Filter,
        k: int = 5,
        *,
        collection_name: str | None = None,
        score_threshold: float | None = None,
        with_payload: bool | Sequence[str] = True,
        with_vectors: bool | Sequence[str] = False,
    ) -> list[ScoredPoint]:
        resolved_collection = self._resolve_collection_name(collection_name)
        response = await self._client.query_points(
            collection_name=resolved_collection,
            query=list(query_vector),
            query_filter=query_filter,
            limit=k,
            score_threshold=score_threshold,
            with_payload=with_payload,
            with_vectors=with_vectors,
        )
        return cast(list[ScoredPoint], response.points)

    async def get_points(
        self,
        ids: Sequence[PointId],
        *,
        collection_name: str | None = None,
        with_payload: bool | Sequence[str] = True,
        with_vectors: bool | Sequence[str] = False,
    ) -> list[Record]:
        resolved_collection = self._resolve_collection_name(collection_name)
        result = await self._client.retrieve(
            collection_name=resolved_collection,
            ids=ids,
            with_payload=with_payload,
            with_vectors=with_vectors,
        )
        return cast(list[Record], result)

    async def count(self, collection_name: str | None = None, query_filter: Filter | None = None) -> int:
        resolved_collection = self._resolve_collection_name(collection_name)
        result = await self._client.count(collection_name=resolved_collection, count_filter=query_filter)
        typed_result = cast(CountResult, result)
        return cast(int, typed_result.count)

    async def has_payload_value(
        self,
        *,
        key: str,
        value: int | str,
        collection_name: str | None = None,
    ) -> bool:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
            ]
        )
        return (await self.count(collection_name=collection_name, query_filter=query_filter)) > 0

    async def delete_points(
        self,
        ids: Sequence[PointId],
        *,
        collection_name: str | None = None,
        wait: bool = True,
    ) -> UpdateResult:
        resolved_collection = self._resolve_collection_name(collection_name)
        selector = PointIdsList(points=list(ids))
        return await self._client.delete(
            collection_name=resolved_collection,
            points_selector=selector,
            wait=wait,
        )
