from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, status

from src.api.schemas import (
    CreateMauticFieldRequest,
    MauticFieldResponse,
    UpdateMauticFieldRequest,
    UpdateMauticFieldResponse,
)
from src.mauitc import MauticClient

router = APIRouter(prefix="/mautic", tags=["mautic"])


def _build_field_alias(name: str) -> str:
    normalized = re.sub(r"\s+", "_", name.strip().lower())
    normalized = re.sub(r"[^\w]+", "_", normalized)
    alias = normalized.strip("_")
    return alias or "custom_field"


def _extract_field_payload(payload: Any) -> Mapping[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None

    field_payload = payload.get("field")
    if isinstance(field_payload, Mapping):
        return field_payload

    return payload


@router.post("/field", response_model=MauticFieldResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_field_endpoint(payload: CreateMauticFieldRequest) -> MauticFieldResponse:
    alias = _build_field_alias(payload.name)
    mautic_payload = {
        "label": payload.name,
        "alias": alias,
        "type": "text",
        "object": "lead",
    }

    async with MauticClient() as mautic_client:
        response = await mautic_client.create_contact_field(json=mautic_payload)

    response_payload = _extract_field_payload(response.json())
    field_id = response_payload.get("id") if isinstance(response_payload, Mapping) else None
    raw_name = response_payload.get("label") if isinstance(response_payload, Mapping) else None
    raw_alias = response_payload.get("alias") if isinstance(response_payload, Mapping) else None
    raw_type = response_payload.get("type") if isinstance(response_payload, Mapping) else None
    raw_object = response_payload.get("object") if isinstance(response_payload, Mapping) else None

    return MauticFieldResponse(
        id=field_id if isinstance(field_id, int) else None,
        name=raw_name if isinstance(raw_name, str) and raw_name else payload.name,
        alias=raw_alias if isinstance(raw_alias, str) and raw_alias else alias,
        type=raw_type if isinstance(raw_type, str) and raw_type else "text",
        object=raw_object if isinstance(raw_object, str) and raw_object else "lead",
    )


@router.patch("/field", response_model=UpdateMauticFieldResponse, status_code=status.HTTP_200_OK)
async def update_contact_field_endpoint(payload: UpdateMauticFieldRequest) -> UpdateMauticFieldResponse:
    async with MauticClient() as mautic_client:
        await mautic_client.update_contact(payload.lead_id, json={payload.field: payload.value})

    return UpdateMauticFieldResponse(
        lead_id=payload.lead_id,
        field=payload.field,
        value=payload.value,
        status="updated",
    )
