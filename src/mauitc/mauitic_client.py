from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import Any

import httpx

from src.api_client.api_client import ApiClient
from src.config.settings import AppSettings, get_settings


class MauticClient:
    def __init__(
        self,
        settings: AppSettings | None = None,
        timeout: float | None = None,
        headers: Mapping[str, str] | None = None,
        username: str | None = None,
        password: str | None = None,
        raise_for_status: bool = True,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = ApiClient(
            base_url=self._settings.mautic_api_base_url,
            settings=self._settings,
            timeout=timeout,
            headers=self._resolve_headers(
                headers=headers,
                username=username or self._settings.mautic_api_username,
                password=password or self._settings.mautic_api_password_value,
            ),
            raise_for_status=raise_for_status,
        )

    @staticmethod
    def _build_basic_auth_header(username: str | None, password: str | None) -> str | None:
        resolved_username = (username or "").strip()
        resolved_password = (password or "").strip()
        if not resolved_username or not resolved_password:
            return None

        credentials = f"{resolved_username}:{resolved_password}".encode()
        encoded_credentials = base64.b64encode(credentials).decode("ascii")
        return f"Basic {encoded_credentials}"

    @classmethod
    def _resolve_headers(
        cls,
        *,
        headers: Mapping[str, str] | None,
        username: str | None,
        password: str | None,
    ) -> dict[str, str] | None:
        resolved_headers = dict(headers or {})
        auth_header = cls._build_basic_auth_header(username, password)
        if auth_header and "Authorization" not in resolved_headers:
            resolved_headers["Authorization"] = auth_header
        return resolved_headers

    async def update_contact(
        self,
        contact_id: int | str,
        *,
        json: Any = None,
        data: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        return await self._client.request(
            "PATCH",
            f"/contacts/{contact_id}/edit",
            json=json,
            data=data,
            headers=headers,
            timeout=timeout,
        )

    async def create_contact_field(
        self,
        *,
        json: Any = None,
        data: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        return await self._client.post(
            "/fields/contact/new",
            json=json,
            data=data,
            headers=headers,
            timeout=timeout,
        )

    async def get_contact_activity(
        self,
        lead_id: int | str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        return await self._client.get(
            f"/contacts/{lead_id}/activity",
            params=params,
            headers=headers,
            timeout=timeout,
        )

    async def find_contacts_by_email(
        self,
        email: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        search_params: dict[str, Any] = {"search": f"email:{email}"}
        if params:
            search_params.update(dict(params))
        return await self._client.get(
            "/contacts",
            params=search_params,
            headers=headers,
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> MauticClient:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()
