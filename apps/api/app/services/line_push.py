from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from ..core.config import Settings
from .line_reply import build_menu_flex_message

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
JOB_CATEGORY_LABELS = {
    "spot": "スポット便",
    "charter": "チャーター",
    "regular": "定期便",
    "work": "作業案件",
    "other": "その他",
}


class LinePushError(Exception):
    pass


def push_liff_job_created_message(settings: Settings, group_id: Optional[str], job: dict[str, Any]) -> None:
    if not group_id:
        raise LinePushError("LINE group id is missing")
    if not settings.line_channel_access_token:
        raise LinePushError("LINE channel access token is not configured")

    payload = {
        "to": group_id,
        "messages": [
            {
                "type": "text",
                "text": build_liff_job_created_text(job),
            }
        ],
    }
    try:
        response = httpx.post(
            LINE_PUSH_URL,
            headers={
                "Authorization": f"Bearer {settings.line_channel_access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise LinePushError(f"LINE push request failed: {exc.__class__.__name__}") from exc

    if response.status_code >= 400:
        raise LinePushError(f"LINE push request failed with status {response.status_code}")


def push_menu_message(settings: Settings, user_id: Optional[str], session_id: Optional[str] = None) -> None:
    if not user_id:
        raise LinePushError("LINE user id is missing")
    if not settings.line_channel_access_token:
        raise LinePushError("LINE channel access token is not configured")

    payload = {
        "to": user_id,
        "messages": [build_menu_flex_message(settings, session_id=session_id)],
    }
    try:
        response = httpx.post(
            LINE_PUSH_URL,
            headers={
                "Authorization": f"Bearer {settings.line_channel_access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise LinePushError(f"LINE push request failed: {exc.__class__.__name__}") from exc

    if response.status_code >= 400:
        raise LinePushError(f"LINE push request failed with status {response.status_code}")


def build_liff_job_created_text(job: dict[str, Any]) -> str:
    job_category = _job_category_label(job.get("job_category"))
    pickup = _display_value(job.get("pickup_location"))
    delivery = _display_value(job.get("delivery_location"))
    vehicle_type = _display_value(job.get("vehicle_type"))
    price = _format_price(job.get("price"))
    distance_text = _display_value(job.get("distance_text"))
    standard_fare = _format_price(job.get("standard_fare_yen"))
    fare_ratio = _fare_ratio_text(job.get("fare_ratio_percent"), job.get("fare_judgement"))
    company_name = _display_value(job.get("company_name"))
    contact_name = _display_value(job.get("contact_name") or job.get("contact_display_name"))
    phone_number = _display_value(job.get("phone_number") or job.get("contact_phone") or _first_phone(job.get("phone_numbers")))
    lines = [
        "新規案件が投稿されました",
        "",
        "【案件種別】",
        job_category,
        "",
        "【区間】",
        f"{pickup} → {delivery}",
        "",
        "【車種】",
        vehicle_type,
        "",
        "【距離】",
        distance_text,
        "",
        "【運賃】",
        price,
        "",
        "【標準運賃目安】",
        standard_fare,
        "",
        "【標準比】",
        fare_ratio,
        "",
        "【連絡先】",
        f"会社名：{company_name}",
        f"担当者：{contact_name}",
        f"電話：{phone_number}",
        "",
        "案件一覧から詳細をご確認ください。",
    ]
    return "\n".join(lines)


def notified_at_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _display_value(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "未入力"


def _format_price(value: object) -> str:
    if isinstance(value, bool):
        return "未入力"
    if isinstance(value, int):
        return f"{value:,}円"
    if isinstance(value, float):
        return f"{int(value):,}円"
    if isinstance(value, str) and value.strip():
        try:
            return f"{int(value):,}円"
        except ValueError:
            return value.strip()
    return "未入力"


def _job_category_label(value: object) -> str:
    if isinstance(value, str) and value.strip():
        normalized = value.strip()
        return JOB_CATEGORY_LABELS.get(normalized, normalized)
    return "未入力"


def _fare_ratio_text(ratio: object, judgement: object) -> str:
    if isinstance(ratio, bool) or ratio is None:
        return "未計算"
    if isinstance(ratio, (int, float)):
        ratio_text = f"{round(float(ratio)):.0f}%"
    elif isinstance(ratio, str) and ratio.strip():
        ratio_text = ratio.strip()
    else:
        return "未計算"
    if isinstance(judgement, str) and judgement.strip():
        return f"{ratio_text}（{judgement.strip()}）"
    return ratio_text


def _first_phone(value: object) -> Optional[str]:
    if isinstance(value, list):
        first = next((item for item in value if isinstance(item, str) and item.strip()), None)
        return first.strip() if first else None
    return None
