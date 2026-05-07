from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.config import Settings, get_settings
from ..schemas.liff_forms import LiffJobCreate, LiffVehicleAvailabilityCreate
from ..services.line_push import LinePushError, notified_at_iso, push_liff_job_created_message
from ..services.supabase import (
    create_liff_job,
    create_liff_vehicle_availability,
    fetch_liff_session_by_session_id,
    get_supabase_client,
    mark_liff_session_used,
    SupabaseRequestError,
    supabase_error_fields,
    supabase_error_reason,
    update_job_notification_result,
)

router = APIRouter(prefix="/liff", tags=["liff"])


@router.post("/jobs")
def submit_liff_job(
    payload: LiffJobCreate,
    settings: Settings = Depends(get_settings),
) -> dict[str, dict]:
    supabase = get_supabase_client()
    liff_session = None
    if payload.session_id:
        try:
            liff_session = fetch_liff_session_by_session_id(supabase, payload.session_id)
        except Exception:
            liff_session = None

    try:
        job = create_liff_job(supabase, payload, liff_session=liff_session)
    except SupabaseRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "保存に失敗しました",
                "reason": supabase_error_reason(exc),
                "fields": supabase_error_fields(exc),
                "error_type": "supabase_save_error",
                "payload_keys": exc.payload_keys,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "保存に失敗しました",
                "reason": "API内部処理でエラーが発生しました",
                "fields": [],
                "error_type": "liff_job_save_error",
            },
        ) from exc

    notify_group_id = resolve_liff_job_notify_group_id(settings, job, liff_session)
    if liff_session:
        try:
            mark_liff_session_used(supabase, payload.session_id)
        except Exception:
            pass

    if notify_group_id:
        try:
            push_liff_job_created_message(settings, notify_group_id, job)
            try:
                update_job_notification_result(
                    supabase,
                    job_id=job.get("id") if isinstance(job.get("id"), str) else None,
                    notify_group_id=notify_group_id,
                    notified_at=notified_at_iso(),
                    notify_error=None,
                )
            except Exception:
                pass
        except LinePushError as exc:
            try:
                update_job_notification_result(
                    supabase,
                    job_id=job.get("id") if isinstance(job.get("id"), str) else None,
                    notify_group_id=notify_group_id,
                    notify_error=exc.__class__.__name__,
                )
            except Exception:
                pass
    else:
        try:
            update_job_notification_result(
                supabase,
                job_id=job.get("id") if isinstance(job.get("id"), str) else None,
                notify_group_id=None,
                notify_error="notification_skipped_no_group",
            )
        except Exception:
            pass

    return {"job": job}


@router.post("/vehicle-availabilities")
def submit_vehicle_availability(payload: LiffVehicleAvailabilityCreate) -> dict[str, dict]:
    try:
        vehicle_availability = create_liff_vehicle_availability(get_supabase_client(), payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to submit vehicle availability",
        ) from exc

    return {"vehicle_availability": vehicle_availability}


def resolve_liff_job_notify_group_id(
    settings: Settings,
    job: dict,
    liff_session: dict | None,
) -> str | None:
    if liff_session and isinstance(liff_session.get("source_group_id"), str):
        return liff_session["source_group_id"]
    if isinstance(job.get("notify_group_id"), str) and job["notify_group_id"]:
        return job["notify_group_id"]
    if settings.line_default_notify_group_id:
        return settings.line_default_notify_group_id
    return None
