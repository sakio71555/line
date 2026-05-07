from __future__ import annotations

from typing import Optional

import httpx

from ..core.config import Settings

LINE_API_BASE = "https://api.line.me"


def fetch_line_profile(
    *,
    settings: Settings,
    source_group_id: Optional[str],
    source_user_id: Optional[str],
) -> dict[str, str] | None:
    if not settings.line_channel_access_token or not source_user_id:
        return None

    path = profile_path(source_group_id, source_user_id)
    try:
        response = httpx.get(
            f"{LINE_API_BASE}{path}",
            headers={"Authorization": f"Bearer {settings.line_channel_access_token}"},
            timeout=8,
        )
    except httpx.HTTPError:
        return None

    if response.status_code >= 400:
        return None

    data = response.json()
    payload: dict[str, str] = {}
    display_name = data.get("displayName")
    picture_url = data.get("pictureUrl")
    if isinstance(display_name, str) and display_name:
        payload["display_name"] = display_name
    if isinstance(picture_url, str) and picture_url:
        payload["picture_url"] = picture_url
    return payload or None


def profile_path(source_group_id: Optional[str], source_user_id: str) -> str:
    if source_group_id and source_group_id.startswith("C"):
        return f"/v2/bot/group/{source_group_id}/member/{source_user_id}"
    if source_group_id and source_group_id.startswith("R"):
        return f"/v2/bot/room/{source_group_id}/member/{source_user_id}"
    return f"/v2/bot/profile/{source_user_id}"
