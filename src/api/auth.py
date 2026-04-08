from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.settings import AppSettings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)
bearer_credentials = Depends(bearer_scheme)
settings_dependency = Depends(get_settings)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _encode_segment(payload: dict[str, Any]) -> str:
    return _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _sign(message: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def create_api_key(*, secret: str, settings: AppSettings | None = None) -> str:
    resolved_settings = settings or get_settings()
    expected_secret = resolved_settings.api_auth_secret_value
    if not expected_secret or secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret.")

    issued_at = datetime.now(UTC)
    header = {"alg": resolved_settings.api_jwt_algorithm, "typ": "JWT"}
    payload = {
        "sub": "trusted-integrator",
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(seconds=resolved_settings.api_jwt_expiration_seconds)).timestamp()),
    }
    signing_input = f"{_encode_segment(header)}.{_encode_segment(payload)}"
    signature = _sign(signing_input, resolved_settings.api_auth_secret_value)
    return f"{signing_input}.{signature}"


def decode_api_key(token: str, *, settings: AppSettings | None = None) -> dict[str, Any]:
    resolved_settings = settings or get_settings()
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.") from exc

    signing_input = f"{header_segment}.{payload_segment}"
    expected_signature = _sign(signing_input, resolved_settings.api_auth_secret_value)
    if not hmac.compare_digest(signature_segment, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")

    try:
        header = json.loads(_b64url_decode(header_segment))
        payload = json.loads(_b64url_decode(payload_segment))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.") from exc

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")

    if header.get("alg") != resolved_settings.api_jwt_algorithm or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")

    if exp <= int(datetime.now(UTC).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired.")

    return payload


def require_api_auth(
    credentials: HTTPAuthorizationCredentials | None = bearer_credentials,
    settings: AppSettings = settings_dependency,
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key.")
    return decode_api_key(credentials.credentials, settings=settings)
