from __future__ import annotations

from typing import Optional

import httpx

from ..core.config import Settings

LINE_ID_TOKEN_VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"


class LineAuthError(Exception):
    pass


def bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def verify_line_id_token(settings: Settings, id_token: Optional[str]) -> dict[str, str | None]:
    token = id_token.strip() if isinstance(id_token, str) else ""
    if not token:
        raise LineAuthError("LINE ID token is missing")
    if not settings.line_login_channel_id:
        raise LineAuthError("LINE Login channel id is not configured")

    try:
        response = httpx.post(
            LINE_ID_TOKEN_VERIFY_URL,
            data={
                "id_token": token,
                "client_id": settings.line_login_channel_id,
            },
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LineAuthError(f"LINE ID token verification failed: {exc.__class__.__name__}") from exc

    data = response.json()
    line_user_id = data.get("sub")
    if not isinstance(line_user_id, str) or not line_user_id:
        raise LineAuthError("LINE ID token does not contain a user id")

    display_name = data.get("name")
    return {
        "line_user_id": line_user_id,
        "display_name": display_name if isinstance(display_name, str) else None,
    }

