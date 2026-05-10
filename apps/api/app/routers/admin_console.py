from __future__ import annotations

import secrets
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from ..core.config import Settings, get_settings
from ..schemas.admin_jobs import AdminJobStatusUpdate, AdminJobUpdate
from ..services.supabase import (
    delete_admin_job,
    fetch_admin_console_jobs,
    fetch_admin_console_vehicle_availabilities,
    fetch_admin_job_by_id,
    get_supabase_client,
    restore_admin_console_job,
    set_admin_job_status,
    update_admin_job,
)

router = APIRouter(prefix="/admin-console", tags=["admin-console"])

ENDED_STATUSES = {"assigned", "closed", "completed", "cancelled"}
OPEN_STATUSES = {"open"}


class AdminConsoleRestorePayload(BaseModel):
    status: str = "open"
    reason: Optional[str] = "管理者による復元"

    model_config = ConfigDict(extra="forbid")


def require_admin_console_auth(
    authorization: Optional[str] = Header(default=None),
    x_admin_token: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    expected = settings.admin_console_token or settings.admin_console_password
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin console authentication is not configured",
        )

    supplied = admin_token_from_headers(authorization, x_admin_token)
    if not supplied:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin console authentication is required",
        )

    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin console authentication failed",
        )

    return {"actor": "admin_console"}


@router.get("/jobs")
def list_admin_console_jobs(
    _: dict[str, str] = Depends(require_admin_console_auth),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    posting_type: Optional[str] = None,
    job_category: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    company_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    created_from: Optional[date] = None,
    created_to: Optional[date] = None,
    deleted_only: bool = False,
    open_only: bool = False,
    ended_only: bool = False,
    q: Optional[str] = None,
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, list[dict[str, Any]]]:
    jobs = fetch_admin_console_jobs(get_supabase_client(), limit=limit)
    filtered = [
        job
        for job in jobs
        if matches_admin_console_job(
            job,
            status_filter=status_filter,
            posting_type=posting_type,
            job_category=job_category,
            vehicle_type=vehicle_type,
            company_name=company_name,
            phone_number=phone_number,
            created_from=created_from,
            created_to=created_to,
            deleted_only=deleted_only,
            open_only=open_only,
            ended_only=ended_only,
            q=q,
        )
    ]
    return {"jobs": filtered}


@router.get("/jobs/{job_id}")
def get_admin_console_job(
    job_id: str,
    _: dict[str, str] = Depends(require_admin_console_auth),
) -> dict[str, dict[str, Any]]:
    job = fetch_admin_job_by_id(get_supabase_client(), job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"job": job}


@router.patch("/jobs/{job_id}")
def update_admin_console_job(
    job_id: str,
    payload: AdminJobUpdate,
    _: dict[str, str] = Depends(require_admin_console_auth),
) -> dict[str, dict[str, Any]]:
    update_payload = payload.model_dump(exclude_unset=True)
    if not update_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    if "phone_number" in update_payload:
        phone_number = update_payload.get("phone_number")
        update_payload["contact_phone"] = phone_number
        update_payload["phone_numbers"] = [phone_number] if phone_number else []

    job = update_admin_job(get_supabase_client(), job_id, update_payload)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"job": job}


@router.post("/jobs/{job_id}/status")
def update_admin_console_job_status(
    job_id: str,
    payload: AdminJobStatusUpdate,
    _: dict[str, str] = Depends(require_admin_console_auth),
) -> dict[str, dict[str, Any]]:
    if payload.new_status == "deleted":
        job = delete_admin_job(
            get_supabase_client(),
            job_id,
            deleted_by_line_user_id=None,
            delete_reason=payload.reason or "管理者削除",
            changed_by_name="admin_console",
            source_type="admin_console",
        )
    else:
        job = set_admin_job_status(
            get_supabase_client(),
            job_id,
            new_status=payload.new_status,
            reason=payload.reason,
            changed_by_line_user_id=None,
            changed_by_name="admin_console",
            source_type="admin_console",
        )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"job": job}


@router.post("/jobs/{job_id}/delete")
def delete_admin_console_job(
    job_id: str,
    _: dict[str, str] = Depends(require_admin_console_auth),
) -> dict[str, dict[str, Any]]:
    job = delete_admin_job(
        get_supabase_client(),
        job_id,
        deleted_by_line_user_id=None,
        delete_reason="管理者削除",
        changed_by_name="admin_console",
        source_type="admin_console",
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"job": job}


@router.post("/jobs/{job_id}/restore")
def restore_admin_console_deleted_job(
    job_id: str,
    payload: Optional[AdminConsoleRestorePayload] = None,
    _: dict[str, str] = Depends(require_admin_console_auth),
) -> dict[str, dict[str, Any]]:
    restore_payload = payload or AdminConsoleRestorePayload()
    job = restore_admin_console_job(
        get_supabase_client(),
        job_id,
        restore_status=restore_payload.status,
        reason=restore_payload.reason,
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"job": job}


@router.get("/vehicle-availabilities")
def list_admin_console_vehicle_availabilities(
    _: dict[str, str] = Depends(require_admin_console_auth),
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, list[dict[str, Any]]]:
    vehicle_availabilities = fetch_admin_console_vehicle_availabilities(
        get_supabase_client(),
        limit=limit,
    )
    return {"vehicle_availabilities": vehicle_availabilities}


def admin_token_from_headers(authorization: Optional[str], x_admin_token: Optional[str]) -> Optional[str]:
    if x_admin_token:
        return x_admin_token
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def matches_admin_console_job(
    job: dict[str, Any],
    *,
    status_filter: Optional[str],
    posting_type: Optional[str],
    job_category: Optional[str],
    vehicle_type: Optional[str],
    company_name: Optional[str],
    phone_number: Optional[str],
    created_from: Optional[date],
    created_to: Optional[date],
    deleted_only: bool,
    open_only: bool,
    ended_only: bool,
    q: Optional[str],
) -> bool:
    job_status = str(job.get("status") or "")
    is_deleted = bool(job.get("deleted_at")) or job_status == "deleted"

    if deleted_only and not is_deleted:
        return False
    if open_only and job_status not in OPEN_STATUSES:
        return False
    if ended_only and job_status not in ENDED_STATUSES:
        return False
    if status_filter and job_status != status_filter:
        return False
    if posting_type and job.get("posting_type") != posting_type:
        return False
    if job_category and job.get("job_category") != job_category:
        return False
    if vehicle_type and not contains(job.get("vehicle_type"), vehicle_type):
        return False
    if company_name and not contains(job.get("company_name"), company_name):
        return False
    if phone_number and not contains(normalized_phone(job.get("phone_number") or job.get("contact_phone")), normalized_phone(phone_number)):
        return False
    if created_from or created_to:
        created_date = iso_date(job.get("created_at"))
        if not created_date:
            return False
        if created_from and created_date < created_from:
            return False
        if created_to and created_date > created_to:
            return False
    if q and not matches_keyword(job, q):
        return False
    return True


def matches_keyword(job: dict[str, Any], keyword: str) -> bool:
    fields = [
        "company_name",
        "contact_name",
        "phone_number",
        "contact_phone",
        "title",
        "free_text",
        "notes",
        "pickup_location",
        "pickup_prefecture",
        "pickup_city",
        "pickup_address",
        "delivery_location",
        "delivery_prefecture",
        "delivery_city",
        "delivery_address",
    ]
    needle = normalize_text(keyword)
    phone_needle = normalized_phone(keyword)
    for field in fields:
        value = job.get(field)
        if value is None:
            continue
        if needle and needle in normalize_text(str(value)):
            return True
        if phone_needle and phone_needle in normalized_phone(str(value)):
            return True
    return False


def contains(value: object, keyword: str) -> bool:
    return normalize_text(keyword) in normalize_text(str(value or ""))


def normalize_text(value: str) -> str:
    return re_space(value).lower()


def re_space(value: str) -> str:
    return " ".join(value.replace("\u3000", " ").split())


def normalized_phone(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def iso_date(value: object) -> Optional[date]:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
