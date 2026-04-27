from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query, status

from src.api.schemas import LeadType, PromptResponse, UpdatePromptRequest
from src.services.errors import NotFoundError

router = APIRouter(tags=["prompt"])
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
lead_type_query = Query(..., description="Recommendation type / funnel stage.")


def _get_prompt_path(lead_type: LeadType) -> Path:
    return PROMPTS_DIR / f"{lead_type}.txt"


@router.get("/prompt", response_model=PromptResponse, status_code=status.HTTP_200_OK)
def get_prompt_endpoint(
    lead_type: LeadType = lead_type_query,
) -> PromptResponse:
    prompt_path = _get_prompt_path(lead_type)
    if not prompt_path.exists():
        raise NotFoundError(f"Prompt file for lead_type '{lead_type}' was not found.")

    return PromptResponse(
        lead_type=lead_type,
        prompt=prompt_path.read_text(encoding="utf-8"),
    )


@router.put("/prompt", response_model=PromptResponse, status_code=status.HTTP_200_OK)
def update_prompt_endpoint(payload: UpdatePromptRequest) -> PromptResponse:
    prompt_path = _get_prompt_path(payload.lead_type)
    if not prompt_path.exists():
        raise NotFoundError(f"Prompt file for lead_type '{payload.lead_type}' was not found.")

    prompt_path.write_text(payload.prompt, encoding="utf-8")
    return PromptResponse(lead_type=payload.lead_type, prompt=payload.prompt)
