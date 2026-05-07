from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from ..core.config import Settings, get_settings
from ..schemas.admin_jobs import StatusUpdateApply, StatusUpdateIgnore
from ..services.line_auth import LineAuthError, bearer_token, verify_line_id_token
from ..services.supabase import (
    apply_status_update,
    fetch_admin_job_by_id,
    fetch_admin_status_updates,
    fetch_status_update_by_id,
    get_supabase_client,
    ignore_status_update,
    status_update_target_job_ids,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/status-updates", tags=["admin-status-updates"])


@router.get("")
def list_status_updates(
    scope: Literal["all", "mine"] = Query(default="mine"),
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, list[dict]]:
    owner_line_user_id = resolve_owner_line_user_id(scope, authorization, settings)
    try:
        updates = fetch_admin_status_updates(get_supabase_client(), owner_line_user_id=owner_line_user_id)
    except Exception as exc:
        logger.warning(
            "Admin status updates endpoint failed path=/admin/status-updates error_type=%s",
            exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch status update candidates",
        ) from exc

    return {"status_updates": updates}


@router.post("/{status_update_id}/apply")
def apply_status_update_candidate(
    status_update_id: str,
    payload: StatusUpdateApply,
    scope: Literal["all", "mine"] = Query(default="mine"),
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, dict]:
    actor = authorize_status_update_action(
        status_update_id,
        scope,
        authorization,
        settings,
        job_id=payload.job_id,
    )
    try:
        result = apply_status_update(
            get_supabase_client(),
            status_update_id,
            job_id=payload.job_id,
            new_status=payload.new_status,
            reason=payload.reason,
            changed_by_line_user_id=payload.changed_by_line_user_id or actor.get("line_user_id"),
            changed_by_name=payload.changed_by_name or actor.get("display_name"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to apply status update candidate",
        ) from exc

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status update candidate not found",
        )

    return result


@router.post("/{status_update_id}/ignore")
def ignore_status_update_candidate(
    status_update_id: str,
    payload: StatusUpdateIgnore,
    scope: Literal["all", "mine"] = Query(default="mine"),
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, dict]:
    authorize_status_update_action(status_update_id, scope, authorization, settings)
    try:
        update = ignore_status_update(
            get_supabase_client(),
            status_update_id,
            reviewed_by=payload.reviewed_by,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to ignore status update candidate",
        ) from exc

    if not update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status update candidate not found",
        )

    return {"status_update": update}


def resolve_owner_line_user_id(
    scope: Literal["all", "mine"],
    authorization: Optional[str],
    settings: Settings,
) -> Optional[str]:
    if scope != "mine":
        return None
    try:
        return verify_line_id_token(settings, bearer_token(authorization))["line_user_id"]
    except LineAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LINEログイン確認に失敗しました",
        ) from exc


def authorize_status_update_action(
    status_update_id: str,
    scope: Literal["all", "mine"],
    authorization: Optional[str],
    settings: Settings,
    *,
    job_id: Optional[str] = None,
) -> dict[str, str | None]:
    if scope != "mine":
        return {"line_user_id": None, "display_name": None}

    try:
        auth_result = verify_line_id_token(settings, bearer_token(authorization))
    except LineAuthError as exc:
        logger.info(
            "Admin status update authorization failed endpoint=/admin/status-updates scope=mine status_update_id=%s reason=line_auth_failed has_authorization=%s",
            status_update_id,
            bool(authorization),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LINEログイン確認に失敗しました",
        ) from exc

    status_update = fetch_status_update_by_id(get_supabase_client(), status_update_id)
    if not status_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status update candidate not found",
        )

    target_job_ids = [job_id] if job_id else status_update_target_job_ids(status_update)
    if not target_job_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自分の投稿に紐づく終了報告だけ操作できます",
        )

    owner_match = any(job_is_owned_by(job_id, auth_result["line_user_id"]) for job_id in target_job_ids)
    logger.info(
        "Admin status update authorization checked endpoint=/admin/status-updates scope=mine status_update_id=%s owner_match=%s has_authorization=%s",
        status_update_id,
        owner_match,
        bool(authorization),
    )
    if not owner_match:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自分の投稿に紐づく終了報告だけ操作できます",
        )

    return auth_result


def job_is_owned_by(job_id: Optional[str], line_user_id: str) -> bool:
    if not job_id:
        return False
    job = fetch_admin_job_by_id(get_supabase_client(), job_id)
    return bool(job and job.get("created_by_line_user_id") == line_user_id)
