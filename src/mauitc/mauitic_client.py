from __future__ import annotations

import base64
import re
from collections.abc import Iterable, Mapping
from typing import Any

import httpx
from bs4 import BeautifulSoup, Comment

from src.api_client.api_client import ApiClient
from src.config.settings import AppSettings, get_settings
from src.mauitc.activity_reader import MauticActivityReader


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

    @staticmethod
    def _extract_clean_text(
        html_content: str,
        *,
        preserve_links: bool = True,
        preserve_buttons: bool = False,
    ) -> str:
        soup = BeautifulSoup(html_content, "html.parser")

        for element in soup(["script", "style", "noscript", "meta", "link", "title", "head"]):
            element.decompose()

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        if preserve_links:
            for link in soup.find_all("a"):
                href = link.get("href")
                text = link.get_text(strip=True)
                if isinstance(href, str) and text and not href.startswith("#"):
                    link.string = f"{text} [{href}]"

        if preserve_buttons:
            for button in soup.find_all(["button", "input"], attrs={"type": "button"}):
                raw_text = button.get("value")
                text = raw_text if isinstance(raw_text, str) else button.get_text(strip=True)
                if text:
                    button.string = f"Button: {text}"

        text = soup.get_text()
        lines: list[str] = []
        for line in text.splitlines():
            normalized_line = line.strip()
            if not normalized_line or re.match(r"^[\s\xa0\u200b]*$", normalized_line):
                continue
            lines.append(re.sub(r"\s+", " ", normalized_line))

        return "\n".join(lines)

    @staticmethod
    def _get_first_contact(data: Mapping[str, Any]) -> Mapping[str, Any] | None:
        contacts = data.get("contacts")
        if not isinstance(contacts, dict) or not contacts:
            return None

        first_contact = next(iter(contacts.values()))
        if not isinstance(first_contact, Mapping):
            return None
        return first_contact

    @classmethod
    def _parse_email_payload(
        cls,
        email_id: str,
        email_data: Mapping[str, Any],
        *,
        preserve_links: bool,
        preserve_buttons: bool,
    ) -> dict[str, Any]:
        parsed_email = dict(email_data)
        custom_html = email_data.get("customHtml")
        html_content = custom_html if isinstance(custom_html, str) else ""
        parsed_email["id"] = email_id
        parsed_email["clean_text"] = cls._extract_clean_text(
            html_content,
            preserve_links=preserve_links,
            preserve_buttons=preserve_buttons,
        )
        return parsed_email

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

    async def get_contact_activity_events(
        self,
        lead_id: int | str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        include_types: Iterable[str] | None = None,
        exclude_types: Iterable[str] | None = None,
        parse_only: bool = True,
        keep_raw: bool = False,
    ) -> list[dict[str, Any]]:
        response = await self.get_contact_activity(
            lead_id=lead_id,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        payload = response.json()
        if not isinstance(payload, Mapping):
            return []
        return MauticActivityReader.read_events(
            payload,
            include_types=include_types,
            exclude_types=exclude_types,
            parse_only=parse_only,
            keep_raw=keep_raw,
        )

    async def get_digital_footprint(
        self,
        lead_id: int | str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        return await self.get_contact_activity_events(
            lead_id=lead_id,
            params=params,
            headers=headers,
            timeout=timeout,
            parse_only=False,
            keep_raw=False,
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

    async def get_contacts_count_by_email(
        self,
        email: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> tuple[int, int | None]:
        response = await self.find_contacts_by_email(email, headers=headers, timeout=timeout)
        data = response.json()

        total_raw = data.get("total")
        try:
            total = int(total_raw)
        except (ValueError, TypeError):
            contacts_raw = data.get("contacts")
            total = len(contacts_raw) if isinstance(contacts_raw, dict) else 0

        if total != 1:
            return total, None

        contacts = data.get("contacts")
        if not isinstance(contacts, dict) or not contacts:
            return total, None

        contact_id_str = next(iter(contacts.keys()))
        try:
            return total, int(contact_id_str)
        except (ValueError, TypeError):
            return total, None

    async def get_stages(
        self,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        response = await self._client.get(
            "/stages",
            params=params,
            headers=headers,
            timeout=timeout,
        )
        data = response.json()
        stages = data.get("stages")
        if not isinstance(stages, list):
            return []

        return [dict(stage) for stage in stages if isinstance(stage, Mapping)]

    async def get_contact_stage(
        self,
        *,
        contact_id: int | str | None = None,
        email: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        if (contact_id is None) == (email is None):
            raise ValueError("Pass exactly one of contact_id or email.")

        if email is not None:
            response = await self.find_contacts_by_email(
                email,
                headers=headers,
                timeout=timeout,
            )
            contact = self._get_first_contact(response.json())
            if contact is None:
                return None
            stage = contact.get("stage")
            return dict(stage) if isinstance(stage, Mapping) else None

        response = await self._client.get(
            f"/contacts/{contact_id}",
            headers=headers,
            timeout=timeout,
        )
        data = response.json()
        contact = data.get("contact")
        if not isinstance(contact, Mapping):
            return None
        stage = contact.get("stage")
        return dict(stage) if isinstance(stage, Mapping) else None

    async def save_recommendation(
        self,
        contact_id: int | str,
        recommendation_text: str,
        *,
        field_alias: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        resolved_field_alias = (field_alias or self._settings.mautic_recommendation_field_alias).strip()
        if not resolved_field_alias:
            raise ValueError("Mautic recommendation field alias is not configured.")
        return await self.update_contact(
            contact_id,
            json={resolved_field_alias: recommendation_text},
            headers=headers,
            timeout=timeout,
        )

    async def get_emails(
        self,
        email_id: int | str | None = None,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        preserve_links: bool = True,
        preserve_buttons: bool = False,
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        endpoint = "/emails" if email_id is None else f"/emails/{email_id}"
        response = await self._client.get(
            endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        data = response.json()

        if email_id is not None:
            email_payload = data.get("email")
            if not isinstance(email_payload, Mapping):
                emails_payload = data.get("emails")
                if isinstance(emails_payload, Mapping):
                    fallback_payload = emails_payload.get(str(email_id))
                    email_payload = fallback_payload if isinstance(fallback_payload, Mapping) else None
            if not isinstance(email_payload, Mapping):
                return None

            return self._parse_email_payload(
                str(email_id),
                email_payload,
                preserve_links=preserve_links,
                preserve_buttons=preserve_buttons,
            )

        emails_payload = data.get("emails")
        if not isinstance(emails_payload, Mapping):
            return []

        parsed_emails: list[dict[str, Any]] = []
        for current_email_id, current_email_data in emails_payload.items():
            if not isinstance(current_email_id, str | int):
                continue
            if not isinstance(current_email_data, Mapping):
                continue
            parsed_emails.append(
                self._parse_email_payload(
                    str(current_email_id),
                    current_email_data,
                    preserve_links=preserve_links,
                    preserve_buttons=preserve_buttons,
                )
            )

        return parsed_emails

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> MauticClient:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()
