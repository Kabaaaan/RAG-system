from __future__ import annotations

from fastapi import APIRouter, status

from src.api.auth import create_api_key
from src.api.schemas import AuthKeyRequest, AuthKeyResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/key", response_model=AuthKeyResponse, status_code=status.HTTP_200_OK)
def issue_api_key_endpoint(payload: AuthKeyRequest) -> AuthKeyResponse:
    return AuthKeyResponse(api_key=create_api_key(secret=payload.secret))
