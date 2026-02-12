from collections.abc import Mapping
from typing import Any, Literal

import httpx

from src.config.settings import AppSettings, get_settings


class ApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        settings: AppSettings | None = None,
        api_target: Literal["llm", "embedding"] = "llm",
        timeout: float | None = None,
        headers: Mapping[str, str] | None = None,
        bearer_token: str | None = None,
        raise_for_status: bool = True,
    ) -> None:
        self._settings = settings or get_settings()
        resolved_base_url = (base_url or self._resolve_base_url(api_target)).strip()
        if not resolved_base_url:
            raise ValueError("API base_url is not set. Configure LLM_API_URL or EMBEDDING_MODEL_API_URL.")
        self._base_url = resolved_base_url.rstrip("/")

        self._raise_for_status = raise_for_status
        self._headers = self._build_default_headers(
            headers=headers,
            bearer_token=bearer_token,
            fallback_token=self._resolve_bearer_token(api_target),
        )
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout or self._settings.api_timeout_seconds,
            headers=self._headers,
        )

    @staticmethod
    def _build_default_headers(
        *,
        headers: Mapping[str, str] | None,
        bearer_token: str | None,
        fallback_token: str | None,
    ) -> dict[str, str]:
        base_headers: dict[str, str] = {"Accept": "application/json"}
        if headers:
            base_headers.update(dict(headers))

        token = (bearer_token or fallback_token or "").strip()
        if token and "Authorization" not in base_headers:
            base_headers["Authorization"] = f"Bearer {token}"
        return base_headers

    def _resolve_base_url(self, api_target: Literal["llm", "embedding"]) -> str:
        if api_target == "embedding":
            return self._settings.embedding_api_base_url
        return self._settings.llm_api_base_url

    def _resolve_bearer_token(self, api_target: Literal["llm", "embedding"]) -> str | None:
        if api_target == "embedding":
            return self._settings.embedding_api_bearer_token
        return self._settings.llm_api_bearer_token

    def set_bearer_token(self, token: str) -> None:
        self._client.headers["Authorization"] = f"Bearer {token}"

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        request_url = self._normalize_request_url(url)
        response = await self._client.request(
            method=method,
            url=request_url,
            params=params,
            json=json,
            data=data,
            headers=headers,
            timeout=timeout,
        )
        if self._raise_for_status:
            response.raise_for_status()
        return response

    def _normalize_request_url(self, url: str) -> str:
        # If base URL already points to a concrete endpoint (e.g. .../chat/completions),
        # empty relative URL may become .../chat/completions/ and break strict routers.
        if not url or not url.strip():
            return self._base_url
        return url

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        return await self.request("GET", url, params=params, headers=headers, timeout=timeout)

    async def post(
        self,
        url: str,
        *,
        json: Any = None,
        data: Any = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        return await self.request(
            "POST",
            url,
            json=json,
            data=data,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    async def put(
        self,
        url: str,
        *,
        json: Any = None,
        data: Any = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        return await self.request(
            "PUT",
            url,
            json=json,
            data=data,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    async def delete(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        return await self.request("DELETE", url, params=params, headers=headers, timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ApiClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()

    @classmethod
    def for_llm(cls, *, settings: AppSettings | None = None, **kwargs: Any) -> "ApiClient":
        return cls(settings=settings, api_target="llm", **kwargs)

    @classmethod
    def for_embeddings(cls, *, settings: AppSettings | None = None, **kwargs: Any) -> "ApiClient":
        return cls(settings=settings, api_target="embedding", **kwargs)
