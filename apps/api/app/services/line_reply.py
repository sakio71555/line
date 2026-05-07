from __future__ import annotations

from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from ..core.config import Settings

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
MenuTab = Literal["list", "post", "vehicle", "admin", "companies"]


class LineReplyError(Exception):
    pass


def reply_menu_message(settings: Settings, reply_token: str | None, session_id: str | None = None) -> None:
    if not reply_token:
        raise LineReplyError("LINE reply token is missing")
    if not settings.line_channel_access_token:
        raise LineReplyError("LINE channel access token is not configured")

    payload = {
        "replyToken": reply_token,
        "messages": [build_menu_flex_message(settings, session_id=session_id)],
    }
    try:
        response = httpx.post(
            LINE_REPLY_URL,
            headers={
                "Authorization": f"Bearer {settings.line_channel_access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise LineReplyError(f"LINE reply request failed: {exc.__class__.__name__}") from exc

    if response.status_code >= 400:
        raise LineReplyError(f"LINE reply request failed with status {response.status_code}")


def build_menu_flex_message(settings: Settings, session_id: str | None = None) -> dict[str, Any]:
    return {
        "type": "flex",
        "altText": "案件登録メニュー",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "案件登録メニュー",
                        "weight": "bold",
                        "size": "lg",
                    },
                    {
                        "type": "text",
                        "text": "案件投稿・空車登録・案件一覧・企業検索はこちらから開けます。",
                        "wrap": True,
                        "size": "sm",
                        "color": "#4f675a",
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    menu_button("案件を投稿", build_liff_url(settings, "post", session_id=session_id)),
                    menu_button("空車を登録", build_liff_url(settings, "vehicle", session_id=session_id)),
                    menu_button("案件一覧を見る", build_liff_url(settings, "list", session_id=session_id)),
                    menu_button("管理画面を開く", build_liff_url(settings, "admin", session_id=session_id)),
                    menu_button("企業検索", build_liff_url(settings, "companies", session_id=session_id)),
                ],
            },
        },
    }


def menu_button(label: str, uri: str) -> dict[str, Any]:
    return {
        "type": "button",
        "style": "primary",
        "height": "sm",
        "action": {
            "type": "uri",
            "label": label,
            "uri": uri,
        },
    }


def build_liff_url(settings: Settings, tab: MenuTab, session_id: str | None = None) -> str:
    if settings.liff_base_url:
        base_url = settings.liff_base_url.strip()
    elif settings.liff_id:
        base_url = f"https://liff.line.me/{settings.liff_id.strip()}"
    else:
        raise LineReplyError("LIFF URL is not configured")

    params = {"tab": tab}
    if session_id:
        params["session_id"] = session_id
    return append_query(base_url, params)


def append_query(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
