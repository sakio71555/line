from __future__ import annotations

import json
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Optional

import httpx

from ..core.config import get_settings
from ..schemas.job_analysis import JobAnalysisResult
from ..schemas.jobs import RawLineJobCreate
from .llm_parser import is_review_required

logger = logging.getLogger(__name__)


class SupabaseRequestError(RuntimeError):
    def __init__(
        self,
        *,
        operation: str,
        table: str,
        status_code: Optional[int] = None,
        message: str = "",
        payload_keys: Optional[list[str]] = None,
    ) -> None:
        super().__init__(message or operation)
        self.operation = operation
        self.table = table
        self.status_code = status_code
        self.message = message
        self.payload_keys = payload_keys or []


LIFF_JOB_INSERT_COLUMNS = frozenset(
    {
        "source_type",
        "source_group_id",
        "source_line_message_id",
        "raw_text",
        "posting_type",
        "title",
        "free_text",
        "target_area",
        "job_category",
        "pickup_location",
        "delivery_location",
        "pickup_prefecture",
        "pickup_city",
        "pickup_address",
        "delivery_prefecture",
        "delivery_city",
        "delivery_address",
        "scheduled_date",
        "scheduled_time_text",
        "delivery_date",
        "delivery_time_text",
        "vehicle_type",
        "vehicle_count",
        "cargo_type",
        "price",
        "posted_fare_yen",
        "distance_km",
        "distance_text",
        "distance_source",
        "standard_fare_yen",
        "fare_ratio_percent",
        "fare_ratio_text",
        "fare_judgement",
        "fare_calc_status",
        "fare_calc_note",
        "fare_region",
        "fare_vehicle_class",
        "fare_vehicle_label",
        "tax_type",
        "fee_note",
        "highway_fee_note",
        "company_name",
        "contact_name",
        "phone_number",
        "phone_numbers",
        "contact_line_user_id",
        "contact_display_name",
        "contact_phone",
        "contact_method",
        "contact_missing",
        "notes",
        "status",
        "analysis_status",
        "review_required",
        "missing_fields",
        "created_by_line_user_id",
        "created_by_display_name",
        "notify_group_id",
    }
)


ADMIN_JOB_SELECT = ",".join(
    [
        "id",
        "source_type",
        "source_line_message_id",
        "source_group_id",
        "source_user_id",
        "source_message_id",
        "raw_text",
        "posting_type",
        "title",
        "free_text",
        "target_area",
        "job_category",
        "pickup_location",
        "delivery_location",
        "pickup_prefecture",
        "pickup_city",
        "pickup_address",
        "delivery_prefecture",
        "delivery_city",
        "delivery_address",
        "scheduled_date",
        "scheduled_time_text",
        "delivery_date",
        "posted_at",
        "pickup_date",
        "pickup_time_text",
        "delivery_time_text",
        "schedule_text",
        "date_confidence",
        "date_needs_review",
        "recurring",
        "import_batch_id",
        "history_message_hash",
        "vehicle_type",
        "vehicle_count",
        "cargo_type",
        "price",
        "posted_fare_yen",
        "distance_km",
        "distance_text",
        "distance_source",
        "standard_fare_yen",
        "fare_ratio_percent",
        "fare_ratio_text",
        "fare_judgement",
        "fare_calc_status",
        "fare_calc_note",
        "fare_region",
        "fare_vehicle_class",
        "fare_vehicle_label",
        "tax_type",
        "fee_note",
        "highway_fee_note",
        "budget_note",
        "company_name",
        "contact_name",
        "phone_number",
        "contact_line_user_id",
        "contact_display_name",
        "contact_phone",
        "contact_method",
        "contact_missing",
        "phone_numbers",
        "notes",
        "status",
        "analysis_status",
        "confidence",
        "missing_fields",
        "review_required",
        "created_by_line_user_id",
        "created_by_display_name",
        "assigned_at",
        "in_progress_at",
        "completed_at",
        "cancelled_at",
        "status_updated_at",
        "status_updated_by",
        "closed_reason",
        "closed_reported_by_line_user_id",
        "closed_reported_at",
        "deleted_at",
        "deleted_by_line_user_id",
        "delete_reason",
        "notify_group_id",
        "notified_at",
        "notify_error",
        "created_at",
        "updated_at",
    ]
)

STATUS_UPDATE_SELECT = ",".join(
    [
        "id",
        "source_line_message_id",
        "source_group_id",
        "source_user_id",
        "source_message_id",
        "raw_text",
        "update_type",
        "proposed_status",
        "possible_job_id",
        "candidates",
        "confidence",
        "review_required",
        "reason",
        "created_at",
        "reviewed_at",
        "reviewed_by",
        "applied_at",
        "ignored_at",
        "reported_by_line_user_id",
        "reported_by_display_name",
        "is_reported_by_job_owner",
    ]
)

BASE_STATUS_UPDATE_SELECT = ",".join(
    [
        "id",
        "source_line_message_id",
        "source_group_id",
        "source_user_id",
        "source_message_id",
        "raw_text",
        "update_type",
        "proposed_status",
        "possible_job_id",
        "candidates",
        "confidence",
        "review_required",
        "reason",
        "created_at",
        "reviewed_at",
        "reviewed_by",
        "applied_at",
        "ignored_at",
    ]
)

LINE_MESSAGE_SELECT = ",".join(
    [
        "id",
        "source_type",
        "source_group_id",
        "source_user_id",
        "source_display_name",
        "source_message_id",
        "event_type",
        "message_type",
        "raw_text",
        "attachment_type",
        "attachment_file_name",
        "attachment_message_id",
        "is_unsent",
        "received_at",
        "posted_at",
        "history_date",
        "history_time",
        "import_batch_id",
        "history_message_hash",
        "created_at",
        "classification_confidence",
        "classification_reason",
        "processed_at",
        "processing_error",
    ]
)

VEHICLE_AVAILABILITY_SELECT = ",".join(
    [
        "id",
        "source_type",
        "source_group_id",
        "source_user_id",
        "location",
        "prefecture",
        "vehicle_type",
        "available_from",
        "available_date",
        "company_name",
        "contact_name",
        "contact_phone",
        "phone_numbers",
        "status",
        "review_required",
        "confidence",
        "notes",
        "raw_text",
        "posted_at",
        "created_at",
        "updated_at",
    ]
)


@dataclass(frozen=True)
class SupabaseRestClient:
    url: str
    key: str

    @property
    def rest_url(self) -> str:
        return f"{self.url.rstrip('/')}/rest/v1"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }


@lru_cache
def get_supabase_client() -> SupabaseRestClient:
    settings = get_settings()
    return SupabaseRestClient(settings.supabase_url, settings.supabase_backend_key)


def save_raw_line_job(client: SupabaseRestClient, raw_job: RawLineJobCreate) -> dict:
    headers = {
        **client.headers,
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    response = httpx.post(
        f"{client.rest_url}/jobs",
        params={"on_conflict": "source_message_id"},
        headers=headers,
        json={
            **raw_job.model_dump(exclude_none=True),
            "source_type": "line_group",
            "status": "needs_review",
            "review_required": True,
        },
        timeout=15,
    )

    response.raise_for_status()
    data = response.json()

    if not data:
        return {}

    return data[0]


def insert_row(client: SupabaseRestClient, table: str, payload: dict[str, Any]) -> dict[str, Any]:
    compact_payload = _compact_payload(payload)
    try:
        response = httpx.post(
            f"{client.rest_url}/{table}",
            headers={**client.headers, "Prefer": "return=representation"},
            json=compact_payload,
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise_supabase_request_error(
            operation="insert",
            table=table,
            exc=exc,
            payload_keys=sorted(compact_payload.keys()),
        )
    data = response.json()
    return data[0] if data else {}


def update_rows(
    client: SupabaseRestClient,
    table: str,
    filters: dict[str, str],
    payload: dict[str, Any],
    *,
    select: Optional[str] = None,
) -> list[dict[str, Any]]:
    params = {**filters}
    if select:
        params["select"] = select
    compact_payload = _compact_payload(payload)
    try:
        response = httpx.patch(
            f"{client.rest_url}/{table}",
            params=params,
            headers={**client.headers, "Prefer": "return=representation"},
            json=compact_payload,
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise_supabase_request_error(
            operation="update",
            table=table,
            exc=exc,
            payload_keys=sorted(compact_payload.keys()),
        )
    return response.json()


def delete_rows(
    client: SupabaseRestClient,
    table: str,
    filters: dict[str, str],
) -> list[dict[str, Any]]:
    try:
        response = httpx.delete(
            f"{client.rest_url}/{table}",
            params=filters,
            headers={**client.headers, "Prefer": "return=representation"},
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise_supabase_request_error(
            operation="delete",
            table=table,
            exc=exc,
            payload_keys=[],
        )
    return response.json()


def save_line_message(client: SupabaseRestClient, payload: dict[str, Any]) -> dict[str, Any]:
    return insert_row(client, "line_messages", payload)


def create_liff_session(client: SupabaseRestClient, line_message: dict[str, Any]) -> dict[str, Any]:
    source_group_id = _group_or_room_id(line_message.get("source_group_id"))
    return insert_row(
        client,
        "line_liff_sessions",
        {
            "session_id": secrets.token_urlsafe(24),
            "source_group_id": source_group_id,
            "source_user_id": line_message.get("source_user_id"),
            "source_line_message_id": line_message.get("id"),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
    )


def fetch_liff_session_by_session_id(
    client: SupabaseRestClient,
    session_id: Optional[str],
) -> Optional[dict[str, Any]]:
    if not session_id:
        return None

    response = httpx.get(
        f"{client.rest_url}/line_liff_sessions",
        params={
            "select": "id,session_id,source_group_id,source_user_id,source_line_message_id,created_at,expires_at,used_at",
            "session_id": f"eq.{session_id}",
            "expires_at": f"gte.{datetime.now(timezone.utc).isoformat()}",
            "used_at": "is.null",
            "limit": "1",
        },
        headers=client.headers,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else None


def mark_liff_session_used(client: SupabaseRestClient, session_id: Optional[str]) -> None:
    if not session_id:
        return

    update_rows(
        client,
        "line_liff_sessions",
        {"session_id": f"eq.{session_id}"},
        {"used_at": datetime.now(timezone.utc).isoformat()},
    )


def upsert_line_user(
    client: SupabaseRestClient,
    *,
    line_user_id: Optional[str],
    display_name: Optional[str] = None,
    picture_url: Optional[str] = None,
    company_name: Optional[str] = None,
    contact_name: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not line_user_id:
        return None

    payload = {
        "line_user_id": line_user_id,
        "display_name": display_name,
        "picture_url": picture_url,
        "company_name": company_name,
        "contact_name": contact_name,
        "phone_number": phone_number,
    }
    compact_payload = _compact_payload(payload)
    try:
        response = httpx.post(
            f"{client.rest_url}/line_users",
            params={"on_conflict": "line_user_id"},
            headers={**client.headers, "Prefer": "resolution=merge-duplicates,return=representation"},
            json=compact_payload,
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise_supabase_request_error(
            operation="upsert",
            table="line_users",
            exc=exc,
            payload_keys=sorted(compact_payload.keys()),
        )
    data = response.json()
    return data[0] if data else None


def mark_line_message_processed(
    client: SupabaseRestClient,
    line_message_id: str,
    *,
    processing_error: Optional[str] = None,
) -> None:
    update_rows(
        client,
        "line_messages",
        {"id": f"eq.{line_message_id}"},
        {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "processing_error": processing_error[:500] if processing_error else None,
        },
    )


def mark_unsent_message(client: SupabaseRestClient, source_message_id: str) -> None:
    update_rows(
        client,
        "line_messages",
        {"source_message_id": f"eq.{source_message_id}"},
        {"is_unsent": True},
    )
    update_rows(
        client,
        "jobs",
        {"source_message_id": f"eq.{source_message_id}"},
        {
            "status": "hidden",
            "review_required": True,
            "closed_reason": "LINE message unsent",
            "status_updated_at": datetime.now(timezone.utc).isoformat(),
            "status_updated_by": "system",
        },
    )


def create_job_from_line_message(
    client: SupabaseRestClient,
    payload: dict[str, Any],
) -> dict[str, Any]:
    headers = {
        **client.headers,
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    response = httpx.post(
        f"{client.rest_url}/jobs",
        params={"on_conflict": "source_message_id"},
        headers=headers,
        json=_compact_payload(payload),
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else {}


def create_vehicle_availability(
    client: SupabaseRestClient,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return insert_row(client, "vehicle_availabilities", payload)


def create_status_update_from_line_message(
    client: SupabaseRestClient,
    *,
    line_message: dict[str, Any],
    raw_text: str,
    update_type: str,
    proposed_status: str,
    confidence: float,
    reason: str,
    line_user: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    candidates = find_status_update_candidates(
        client,
        source_group_id=line_message.get("source_group_id"),
        source_user_id=line_message.get("source_user_id"),
    )
    possible_job_id = candidates[0]["id"] if len(candidates) == 1 else None
    reported_by_line_user_id = line_message.get("source_user_id")
    possible_job = candidates[0] if possible_job_id else None
    is_reported_by_owner = is_job_owner_report(possible_job, reported_by_line_user_id)
    adjusted_confidence = min(confidence + 0.08, 0.98) if is_reported_by_owner else confidence
    payload = {
        "source_line_message_id": line_message.get("id"),
        "source_group_id": line_message.get("source_group_id"),
        "source_user_id": line_message.get("source_user_id"),
        "source_message_id": line_message.get("source_message_id"),
        "raw_text": raw_text,
        "update_type": update_type,
        "proposed_status": proposed_status,
        "possible_job_id": possible_job_id,
        "candidates": candidates,
        "confidence": adjusted_confidence,
        "review_required": True,
        "reason": reason,
        "reported_by_line_user_id": reported_by_line_user_id,
        "reported_by_display_name": (line_user or {}).get("display_name"),
        "is_reported_by_job_owner": is_reported_by_owner,
    }
    return insert_row(client, "job_status_updates", payload)


def find_status_update_candidates(
    client: SupabaseRestClient,
    *,
    source_group_id: Optional[str],
    source_user_id: Optional[str],
) -> list[dict[str, Any]]:
    if not source_group_id:
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    response = httpx.get(
        f"{client.rest_url}/jobs",
        params={
            "select": "id,source_group_id,source_user_id,created_by_line_user_id,created_by_display_name,pickup_location,delivery_location,status,company_name,contact_name,created_at",
            "source_group_id": f"eq.{source_group_id}",
            "status": "in.(open,negotiating,needs_review,assigned,in_progress)",
            "created_at": f"gte.{cutoff}",
            "order": "created_at.desc",
            "limit": "20",
        },
        headers=client.headers,
        timeout=15,
    )
    response.raise_for_status()
    rows = response.json()
    now = datetime.now(timezone.utc)

    def score(row: dict[str, Any]) -> tuple[int, float]:
        row_created = _parse_datetime(row.get("created_at"))
        hours_old = (now - row_created).total_seconds() / 3600 if row_created else 999
        same_user = bool(
            source_user_id
            and (
                row.get("source_user_id") == source_user_id
                or row.get("created_by_line_user_id") == source_user_id
            )
        )
        within_24 = hours_old <= 24
        return (2 if same_user else 0) + (2 if within_24 else 0), -hours_old

    rows.sort(key=score, reverse=True)
    return rows[:5]


def create_liff_job(
    client: SupabaseRestClient,
    form: Any,
    liff_session: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    contact_missing = not (form.company_name and form.contact_name and form.phone_number)
    source_group_id = _str_or_none((liff_session or {}).get("source_group_id"))
    source_line_message_id = _str_or_none((liff_session or {}).get("source_line_message_id"))
    if form.line_user_id:
        try:
            upsert_line_user(
                client,
                line_user_id=form.line_user_id,
                display_name=form.display_name,
                company_name=form.company_name,
                contact_name=form.contact_name,
                phone_number=form.phone_number,
            )
        except Exception:
            pass
    posting_type = form.posting_type or "delivery"
    is_other_posting = posting_type == "other"
    pickup_location = " ".join(
        value for value in [form.pickup_prefecture, form.pickup_city, form.pickup_address] if value
    )
    delivery_location = " ".join(
        value
        for value in [form.delivery_prefecture, form.delivery_city, form.delivery_address]
        if value
    )
    fare_calc_status = form.fare_calc_status or "not_calculated"
    if is_other_posting and fare_calc_status == "not_calculated":
        fare_calc_status = "not_applicable"
    fare_calc_note = form.fare_calc_note or (
        "積地・卸地を指定しない案件のため" if is_other_posting else None
    )
    raw_text_parts = [
        f"投稿タイプ: {posting_type}",
        f"案件種別: {form.job_category}",
        f"タイトル: {form.title or ''}",
        f"対象エリア: {form.target_area or ''}",
        f"案件本文: {form.free_text or ''}",
        f"積地: {pickup_location}",
        f"卸地: {delivery_location}",
        f"集荷日: {form.scheduled_date or ''}",
        f"集荷時間: {form.scheduled_time_text or ''}",
        f"納品日: {form.delivery_date or ''}",
        f"納品時間: {form.delivery_time_text or ''}",
        f"車種: {form.vehicle_type or ''}",
        f"台数: {form.vehicle_count}",
        f"荷物: {form.cargo_type or ''}",
        f"運賃: {form.price if form.price is not None else ''}",
        f"走行距離: {form.distance_text or ''}",
        f"標準運賃目安: {form.standard_fare_yen if form.standard_fare_yen is not None else ''}",
        f"標準比: {form.fare_ratio_percent if form.fare_ratio_percent is not None else ''}",
        f"税区分: {form.tax_type}",
        f"高速代: {form.highway_fee_note or ''}",
        f"手数料: {form.fee_note or ''}",
        f"会社名: {form.company_name or ''}",
        f"担当者: {form.contact_name or ''}",
        f"電話番号: {form.phone_number or ''}",
        f"備考: {form.notes or ''}",
    ]
    payload = {
        "source_type": "liff_form",
        "source_group_id": source_group_id,
        "source_line_message_id": source_line_message_id,
        "raw_text": "\n".join(raw_text_parts),
        "posting_type": posting_type,
        "title": form.title,
        "free_text": form.free_text,
        "target_area": form.target_area,
        "job_category": form.job_category,
        "pickup_location": pickup_location or None,
        "delivery_location": delivery_location or None,
        "pickup_prefecture": form.pickup_prefecture,
        "pickup_city": form.pickup_city,
        "pickup_address": form.pickup_address,
        "delivery_prefecture": form.delivery_prefecture,
        "delivery_city": form.delivery_city,
        "delivery_address": form.delivery_address,
        "scheduled_date": form.scheduled_date,
        "scheduled_time_text": form.scheduled_time_text,
        "delivery_date": form.delivery_date,
        "delivery_time_text": form.delivery_time_text,
        "vehicle_type": form.vehicle_type,
        "vehicle_count": form.vehicle_count,
        "cargo_type": form.cargo_type,
        "price": form.price,
        "posted_fare_yen": form.posted_fare_yen if form.posted_fare_yen is not None else form.price,
        "distance_km": form.distance_km,
        "distance_text": form.distance_text,
        "distance_source": form.distance_source,
        "standard_fare_yen": form.standard_fare_yen,
        "fare_ratio_percent": form.fare_ratio_percent,
        "fare_ratio_text": form.fare_ratio_text,
        "fare_judgement": form.fare_judgement,
        "fare_calc_status": fare_calc_status,
        "fare_calc_note": fare_calc_note,
        "fare_region": form.fare_region,
        "fare_vehicle_class": form.fare_vehicle_class,
        "fare_vehicle_label": form.fare_vehicle_label,
        "tax_type": form.tax_type,
        "fee_note": form.fee_note,
        "highway_fee_note": form.highway_fee_note,
        "company_name": form.company_name,
        "contact_name": form.contact_name,
        "phone_number": form.phone_number,
        "phone_numbers": [form.phone_number] if form.phone_number else [],
        "contact_line_user_id": form.line_user_id,
        "contact_display_name": form.display_name,
        "contact_phone": form.phone_number,
        "contact_method": "form",
        "contact_missing": contact_missing,
        "notes": form.notes,
        "status": "open",
        "analysis_status": "form_submitted",
        "review_required": False,
        "missing_fields": [],
        "created_by_line_user_id": form.line_user_id,
        "created_by_display_name": form.display_name,
        "notify_group_id": source_group_id,
    }
    return insert_row(client, "jobs", filter_payload_keys(payload, LIFF_JOB_INSERT_COLUMNS))


def update_job_notification_result(
    client: SupabaseRestClient,
    *,
    job_id: Optional[str],
    notify_group_id: Optional[str],
    notified_at: Optional[str] = None,
    notify_error: Optional[str] = None,
) -> None:
    if not job_id:
        return

    update_rows(
        client,
        "jobs",
        {"id": f"eq.{job_id}"},
        {
            "notify_group_id": notify_group_id,
            "notified_at": notified_at,
            "notify_error": notify_error[:500] if notify_error else None,
        },
    )


def create_liff_vehicle_availability(client: SupabaseRestClient, form: Any) -> dict[str, Any]:
    raw_text = "\n".join(
        [
            f"現在地: {form.prefecture} {form.city}",
            f"車種: {form.vehicle_type}",
            f"空車開始: {form.available_from or ''}",
            f"会社名: {form.company_name or ''}",
            f"担当者: {form.contact_name or ''}",
            f"電話番号: {form.phone_number or ''}",
            f"備考: {form.notes or ''}",
        ]
    )
    payload = {
        "source_type": "liff_form",
        "location": f"{form.prefecture} {form.city}",
        "prefecture": form.prefecture,
        "vehicle_type": form.vehicle_type,
        "available_from": form.available_from,
        "company_name": form.company_name,
        "contact_name": form.contact_name,
        "contact_phone": form.phone_number,
        "phone_numbers": [form.phone_number] if form.phone_number else [],
        "status": "open",
        "review_required": True,
        "notes": form.notes,
        "raw_text": raw_text,
    }
    return create_vehicle_availability(client, payload)


def fetch_vehicle_availabilities(client: SupabaseRestClient, *, limit: int = 100) -> list[dict[str, Any]]:
    response = httpx.get(
        f"{client.rest_url}/vehicle_availabilities",
        params={
            "select": VEHICLE_AVAILABILITY_SELECT,
            "status": "eq.open",
            "order": "created_at.desc",
            "limit": str(min(max(limit, 1), 200)),
        },
        headers=client.headers,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def fetch_job_by_id(client: SupabaseRestClient, job_id: str) -> Optional[dict[str, Any]]:
    response = httpx.get(
        f"{client.rest_url}/jobs",
        params={
            "select": "id,raw_text,status",
            "id": f"eq.{job_id}",
            "limit": "1",
        },
        headers=client.headers,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else None


def fetch_next_unanalyzed_job(client: SupabaseRestClient) -> Optional[dict[str, Any]]:
    response = httpx.get(
        f"{client.rest_url}/jobs",
        params={
            "select": "id,raw_text",
            "analysis_status": "eq.pending",
            "order": "created_at.asc",
            "limit": "1",
        },
        headers=client.headers,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else None


def update_job_analysis(
    client: SupabaseRestClient,
    job_id: str,
    analysis: JobAnalysisResult,
    model_name: str,
) -> dict[str, Any]:
    review_required = is_review_required(analysis)
    analysis_status = "needs_review" if review_required else "parsed"
    payload = analysis.model_dump()
    payload.update(
        {
            "analysis_status": analysis_status,
            "analysis_error": None,
            "analysis_model": model_name,
            "analysis_completed_at": datetime.now(timezone.utc).isoformat(),
            "review_required": review_required,
        }
    )

    response = httpx.patch(
        f"{client.rest_url}/jobs",
        params={"id": f"eq.{job_id}"},
        headers={**client.headers, "Prefer": "return=representation"},
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else {}


def mark_job_analysis_failed(
    client: SupabaseRestClient,
    job_id: str,
    error_message: str,
    model_name: str,
) -> None:
    payload = {
        "analysis_status": "failed",
        "analysis_error": error_message[:500],
        "analysis_model": model_name,
        "analysis_completed_at": datetime.now(timezone.utc).isoformat(),
        "review_required": True,
    }
    response = httpx.patch(
        f"{client.rest_url}/jobs",
        params={"id": f"eq.{job_id}"},
        headers=client.headers,
        json=payload,
        timeout=15,
    )
    response.raise_for_status()


def fetch_admin_jobs(client: SupabaseRestClient, *, owner_line_user_id: Optional[str] = None) -> list[dict[str, Any]]:
    params = {
        "select": ADMIN_JOB_SELECT,
        "status": "in.(needs_review,open,negotiating,assigned,in_progress,completed,cancelled,closed,hidden)",
        "deleted_at": "is.null",
        "order": "created_at.desc",
        "limit": "500",
    }
    if owner_line_user_id:
        params["created_by_line_user_id"] = f"eq.{owner_line_user_id}"

    response = httpx.get(
        f"{client.rest_url}/jobs",
        params=params,
        headers=client.headers,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def fetch_admin_job_by_id(client: SupabaseRestClient, job_id: str) -> Optional[dict[str, Any]]:
    response = httpx.get(
        f"{client.rest_url}/jobs",
        params={
            "select": ADMIN_JOB_SELECT,
            "id": f"eq.{job_id}",
            "limit": "1",
        },
        headers=client.headers,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else None


def update_admin_job(
    client: SupabaseRestClient,
    job_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    response = httpx.patch(
        f"{client.rest_url}/jobs",
        params={"id": f"eq.{job_id}", "select": ADMIN_JOB_SELECT},
        headers={**client.headers, "Prefer": "return=representation"},
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else {}


def delete_admin_job(
    client: SupabaseRestClient,
    job_id: str,
    *,
    deleted_by_line_user_id: Optional[str] = None,
    delete_reason: Optional[str] = "本人による投稿削除",
) -> dict[str, Any]:
    old_job = fetch_admin_job_by_id(client, job_id)
    if not old_job:
        return {}

    deleted_at = datetime.now(timezone.utc).isoformat()
    job = update_admin_job(
        client,
        job_id,
        {
            "status": "deleted",
            "deleted_at": deleted_at,
            "deleted_by_line_user_id": deleted_by_line_user_id,
            "delete_reason": delete_reason,
            "status_updated_at": deleted_at,
            "status_updated_by": "owner",
        },
    )
    insert_job_status_history(
        client,
        job_id=job_id,
        old_status=old_job.get("status"),
        new_status="deleted",
        reason=delete_reason,
        source_type="admin_manual",
        changed_by_line_user_id=deleted_by_line_user_id,
        changed_by_name="owner",
    )
    return job


def verify_admin_job(client: SupabaseRestClient, job_id: str) -> dict[str, Any]:
    old_job = fetch_admin_job_by_id(client, job_id)
    job = update_admin_job(
        client,
        job_id,
        {
            "review_required": False,
            "analysis_status": "verified",
            "status": "open",
            "status_updated_at": datetime.now(timezone.utc).isoformat(),
            "status_updated_by": "admin",
        },
    )
    if old_job and old_job.get("status") != job.get("status"):
        insert_job_status_history(
            client,
            job_id=job_id,
            old_status=old_job.get("status"),
            new_status=job.get("status"),
            reason="管理者確認完了",
            source_type="admin_manual",
            changed_by_name="admin",
        )
    return job


def hide_admin_job(client: SupabaseRestClient, job_id: str) -> dict[str, Any]:
    return set_admin_job_status(
        client,
        job_id,
        new_status="hidden",
        reason="管理者による非公開",
        changed_by_name="admin",
    )


def set_admin_job_status(
    client: SupabaseRestClient,
    job_id: str,
    *,
    new_status: str,
    reason: Optional[str],
    changed_by_line_user_id: Optional[str] = None,
    changed_by_name: Optional[str] = "admin",
    source_type: str = "admin_manual",
    source_line_message_id: Optional[str] = None,
) -> dict[str, Any]:
    old_job = fetch_admin_job_by_id(client, job_id)
    if not old_job:
        return {}

    payload: dict[str, Any] = {
        "status": new_status,
        "status_updated_at": datetime.now(timezone.utc).isoformat(),
        "status_updated_by": changed_by_name,
    }
    if new_status == "assigned":
        payload["assigned_at"] = datetime.now(timezone.utc).isoformat()
    if new_status == "in_progress":
        payload["in_progress_at"] = datetime.now(timezone.utc).isoformat()
    if new_status == "completed":
        payload["completed_at"] = datetime.now(timezone.utc).isoformat()
    if new_status == "cancelled":
        payload["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    if new_status in {"cancelled", "closed", "hidden"}:
        payload["closed_reason"] = reason

    job = update_admin_job(client, job_id, payload)
    insert_job_status_history(
        client,
        job_id=job_id,
        old_status=old_job.get("status"),
        new_status=new_status,
        reason=reason,
        source_type=source_type,
        source_line_message_id=source_line_message_id,
        changed_by_line_user_id=changed_by_line_user_id,
        changed_by_name=changed_by_name,
    )
    return job


def insert_job_status_history(
    client: SupabaseRestClient,
    *,
    job_id: str,
    old_status: Optional[str],
    new_status: Optional[str],
    reason: Optional[str],
    source_type: str,
    source_line_message_id: Optional[str] = None,
    changed_by_line_user_id: Optional[str] = None,
    changed_by_name: Optional[str] = "admin",
) -> dict[str, Any]:
    if not new_status:
        return {}
    return insert_row(
        client,
        "job_status_history",
        {
            "job_id": job_id,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
            "source_type": source_type,
            "source_line_message_id": source_line_message_id,
            "changed_by_line_user_id": changed_by_line_user_id,
            "changed_by_name": changed_by_name,
        },
    )


def fetch_admin_status_updates(
    client: SupabaseRestClient,
    *,
    owner_line_user_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    try:
        rows = fetch_status_update_rows(
            client,
            select=STATUS_UPDATE_SELECT,
            params={
                "applied_at": "is.null",
                "ignored_at": "is.null",
                "order": "created_at.desc",
                "limit": "100",
            },
        )
    except httpx.HTTPStatusError as exc:
        log_safe_supabase_error("fetch admin status updates", exc)
        if not is_missing_column_error(exc):
            return []
        rows = fetch_status_update_rows_or_empty(
            client,
            select=BASE_STATUS_UPDATE_SELECT,
            params={
                "applied_at": "is.null",
                "ignored_at": "is.null",
                "order": "created_at.desc",
                "limit": "100",
            },
            operation="fetch admin status updates fallback",
        )
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        log_safe_error("fetch admin status updates", exc)
        return []

    updates = normalize_status_updates(rows)
    if not owner_line_user_id:
        return updates

    owner_job_ids = {
        _str_or_none(job.get("id"))
        for job in fetch_admin_jobs(client, owner_line_user_id=owner_line_user_id)
    }
    owner_job_ids.discard(None)
    return [
        update
        for update in updates
        if any(job_id in owner_job_ids for job_id in status_update_target_job_ids(update))
    ]


def fetch_status_update_rows(
    client: SupabaseRestClient,
    *,
    select: str,
    params: dict[str, str],
) -> list[dict[str, Any]]:
    response = httpx.get(
        f"{client.rest_url}/job_status_updates",
        params={
            "select": select,
            **params,
        },
        headers=client.headers,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def fetch_status_update_rows_or_empty(
    client: SupabaseRestClient,
    *,
    select: str,
    params: dict[str, str],
    operation: str,
) -> list[dict[str, Any]]:
    try:
        return fetch_status_update_rows(client, select=select, params=params)
    except httpx.HTTPStatusError as exc:
        log_safe_supabase_error(operation, exc)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        log_safe_error(operation, exc)
    return []


def fetch_admin_line_messages(client: SupabaseRestClient) -> list[dict[str, Any]]:
    response = httpx.get(
        f"{client.rest_url}/line_messages",
        params={
            "select": LINE_MESSAGE_SELECT,
            "order": "created_at.desc",
            "limit": "100",
        },
        headers=client.headers,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def fetch_status_update_by_id(
    client: SupabaseRestClient,
    status_update_id: str,
) -> Optional[dict[str, Any]]:
    params = {
        "id": f"eq.{status_update_id}",
        "limit": "1",
    }
    try:
        data = fetch_status_update_rows(client, select=STATUS_UPDATE_SELECT, params=params)
    except httpx.HTTPStatusError as exc:
        log_safe_supabase_error("fetch status update by id", exc)
        if not is_missing_column_error(exc):
            return None
        data = fetch_status_update_rows_or_empty(
            client,
            select=BASE_STATUS_UPDATE_SELECT,
            params=params,
            operation="fetch status update by id fallback",
        )
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        log_safe_error("fetch status update by id", exc)
        return None
    normalized = normalize_status_updates(data)
    return normalized[0] if normalized else None


def apply_status_update(
    client: SupabaseRestClient,
    status_update_id: str,
    *,
    job_id: Optional[str],
    new_status: str,
    reason: Optional[str],
    changed_by_line_user_id: Optional[str],
    changed_by_name: Optional[str],
) -> dict[str, Any]:
    status_update = fetch_status_update_by_id(client, status_update_id)
    if not status_update:
        return {}

    target_job_id = job_id or status_update.get("possible_job_id")
    if not target_job_id:
        raise ValueError("No target job_id for status update")

    job = set_admin_job_status(
        client,
        target_job_id,
        new_status=new_status,
        reason=reason or status_update.get("reason"),
        changed_by_line_user_id=changed_by_line_user_id,
        changed_by_name=changed_by_name,
        source_type="line_status_update_candidate",
        source_line_message_id=status_update.get("source_line_message_id"),
    )
    update_rows(
        client,
        "jobs",
        {"id": f"eq.{target_job_id}"},
        {
            "closed_reported_by_line_user_id": status_update.get("reported_by_line_user_id"),
            "closed_reported_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    job = fetch_admin_job_by_id(client, target_job_id) or job
    update_rows(
        client,
        "job_status_updates",
        {"id": f"eq.{status_update_id}"},
        {
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "reviewed_by": changed_by_name,
            "review_required": False,
            "possible_job_id": target_job_id,
            "proposed_status": new_status,
        },
    )
    return {"job": job, "status_update": fetch_status_update_by_id(client, status_update_id)}


def ignore_status_update(
    client: SupabaseRestClient,
    status_update_id: str,
    *,
    reviewed_by: Optional[str],
) -> dict[str, Any]:
    payload = {
        "ignored_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": reviewed_by,
        "review_required": False,
    }
    try:
        rows = update_rows(
            client,
            "job_status_updates",
            {"id": f"eq.{status_update_id}"},
            payload,
            select=STATUS_UPDATE_SELECT,
        )
    except SupabaseRequestError as exc:
        if "reported_by_display_name" not in exc.message:
            raise
        rows = update_rows(
            client,
            "job_status_updates",
            {"id": f"eq.{status_update_id}"},
            payload,
            select=BASE_STATUS_UPDATE_SELECT,
        )
    normalized = normalize_status_updates(rows)
    return normalized[0] if normalized else {}


def normalize_status_updates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(normalize_status_update(row))
    return normalized


def normalize_status_update(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _str_or_none(row.get("id")) or "",
        "source_line_message_id": _str_or_none(row.get("source_line_message_id")),
        "source_group_id": _str_or_none(row.get("source_group_id")),
        "source_user_id": _str_or_none(row.get("source_user_id")),
        "source_message_id": _str_or_none(row.get("source_message_id")),
        "raw_text": _str_or_none(row.get("raw_text")) or "",
        "update_type": _str_or_none(row.get("update_type")),
        "proposed_status": _str_or_none(row.get("proposed_status")),
        "possible_job_id": _str_or_none(row.get("possible_job_id")),
        "candidates": normalize_status_update_candidates(row.get("candidates")),
        "confidence": _numeric_or_none(row.get("confidence")),
        "review_required": row.get("review_required") if isinstance(row.get("review_required"), bool) else None,
        "reason": _str_or_none(row.get("reason")),
        "created_at": _str_or_none(row.get("created_at")) or "",
        "reviewed_at": _str_or_none(row.get("reviewed_at")),
        "reviewed_by": _str_or_none(row.get("reviewed_by")),
        "applied_at": _str_or_none(row.get("applied_at")),
        "ignored_at": _str_or_none(row.get("ignored_at")),
        "reported_by_line_user_id": _str_or_none(row.get("reported_by_line_user_id")),
        "reported_by_display_name": _str_or_none(row.get("reported_by_display_name")),
        "is_reported_by_job_owner": row.get("is_reported_by_job_owner")
        if isinstance(row.get("is_reported_by_job_owner"), bool)
        else False,
    }


def normalize_status_update_candidates(value: object) -> list[dict[str, Any]]:
    parsed = parse_json_like(value)
    if parsed is None:
        return []
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []

    candidates: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        candidate_id = _str_or_none(item.get("id"))
        if not candidate_id:
            continue
        candidates.append(
            {
                "id": candidate_id,
                "pickup_location": _str_or_none(item.get("pickup_location")),
                "delivery_location": _str_or_none(item.get("delivery_location")),
                "status": _str_or_none(item.get("status")) or "needs_review",
                "created_at": _str_or_none(item.get("created_at")) or "",
            }
        )
    return candidates


def status_update_target_job_ids(update: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    possible_job_id = _str_or_none(update.get("possible_job_id"))
    if possible_job_id:
        ids.append(possible_job_id)
    for candidate in normalize_status_update_candidates(update.get("candidates")):
        candidate_id = _str_or_none(candidate.get("id"))
        if candidate_id and candidate_id not in ids:
            ids.append(candidate_id)
    return ids


def parse_json_like(value: object) -> object:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def _numeric_or_none(value: object) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def log_safe_supabase_error(operation: str, exc: httpx.HTTPStatusError) -> None:
    logger.warning(
        "Supabase request failed operation=%s error_type=%s status=%s message=%s",
        operation,
        exc.__class__.__name__,
        exc.response.status_code,
        safe_supabase_message(exc.response),
    )


def log_safe_error(operation: str, exc: Exception) -> None:
    logger.warning(
        "Supabase operation failed operation=%s error_type=%s",
        operation,
        exc.__class__.__name__,
    )


def safe_supabase_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return ""
    if not isinstance(data, dict):
        return ""
    message = data.get("message")
    if not isinstance(message, str):
        return ""
    return message[:240]


def is_missing_column_error(exc: httpx.HTTPStatusError) -> bool:
    try:
        data = exc.response.json()
    except ValueError:
        data = {}
    code = data.get("code") if isinstance(data, dict) else None
    message = data.get("message") if isinstance(data, dict) else None
    return code == "42703" or (isinstance(message, str) and "does not exist" in message)


def raise_supabase_request_error(
    *,
    operation: str,
    table: str,
    exc: httpx.HTTPStatusError,
    payload_keys: list[str],
) -> None:
    message = safe_supabase_message(exc.response)
    logger.warning(
        "Supabase request failed operation=%s table=%s error_type=%s status=%s message=%s payload_keys=%s",
        operation,
        table,
        exc.__class__.__name__,
        exc.response.status_code,
        message,
        payload_keys,
    )
    raise SupabaseRequestError(
        operation=operation,
        table=table,
        status_code=exc.response.status_code,
        message=message,
        payload_keys=payload_keys,
    ) from exc


def filter_payload_keys(payload: dict[str, Any], allowed_keys: frozenset[str]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key in allowed_keys}


def supabase_error_reason(exc: SupabaseRequestError) -> str:
    message = exc.message
    if re.search(r"(schema cache|Could not find|column .* does not exist|does not exist)", message, re.IGNORECASE):
        return "DBカラム不一致の可能性があります"
    if "source_type" in message and re.search(r"(check constraint|violates|constraint)", message, re.IGNORECASE):
        return "source_type制約エラーの可能性があります"
    if re.search(r"(check constraint|violates|constraint)", message, re.IGNORECASE):
        return "DB制約エラーの可能性があります"
    return "Supabase保存エラー"


def supabase_error_fields(exc: SupabaseRequestError) -> list[str]:
    fields: list[str] = []
    stop_words = {"of", "relation", "table"}
    for pattern in [
        r"'([^']+)' column",
        r'column "([^"]+)"',
        r"column ([a-zA-Z_][a-zA-Z0-9_]*)",
    ]:
        for match in re.finditer(pattern, exc.message):
            field = match.group(1)
            if field not in stop_words and field not in fields:
                fields.append(field)
    return fields


def _compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _str_or_none(value: object) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def _group_or_room_id(value: object) -> Optional[str]:
    if isinstance(value, str) and value.startswith(("C", "R")):
        return value
    return None


def is_job_owner_report(
    job: Optional[dict[str, Any]],
    reported_by_line_user_id: object,
) -> bool:
    if not job or not isinstance(reported_by_line_user_id, str):
        return False
    return job.get("created_by_line_user_id") == reported_by_line_user_id or job.get("source_user_id") == reported_by_line_user_id


def _parse_datetime(value: object) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
