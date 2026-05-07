from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from ..core.config import Settings, get_settings
from ..schemas.admin_jobs import AdminJobStatusUpdate, AdminJobUpdate
from ..services.line_auth import LineAuthError, bearer_token, verify_line_id_token
from ..services.supabase import (
    fetch_admin_job_by_id,
    fetch_admin_jobs,
    get_supabase_client,
    hide_admin_job,
    set_admin_job_status,
    update_admin_job,
    verify_admin_job,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])


@router.get("")
def list_admin_jobs(
    scope: Literal["all", "mine"] = Query(default="mine"),
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, list[dict]]:
    owner_line_user_id = None
    if scope == "mine":
        try:
            auth_result = verify_line_id_token(settings, bearer_token(authorization))
            owner_line_user_id = auth_result["line_user_id"]
        except LineAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LINEログイン確認に失敗しました",
            ) from exc

    try:
        jobs = fetch_admin_jobs(get_supabase_client(), owner_line_user_id=owner_line_user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch jobs",
        ) from exc

    return {"jobs": jobs}


@router.get("/{job_id}")
def get_admin_job(job_id: str) -> dict[str, dict]:
    try:
        job = fetch_admin_job_by_id(get_supabase_client(), job_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch job",
        ) from exc

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return {"job": job}


@router.patch("/{job_id}")
def update_job(
    job_id: str,
    payload: AdminJobUpdate,
    scope: Literal["all", "mine"] = Query(default="mine"),
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, dict]:
    update_payload = payload.model_dump(exclude_unset=True)
    if not update_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    authorize_job_action(job_id, scope, authorization, settings)

    try:
        job = update_admin_job(get_supabase_client(), job_id, update_payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update job",
        ) from exc

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return {"job": job}


@router.post("/{job_id}/status")
def update_job_status(
    job_id: str,
    payload: AdminJobStatusUpdate,
    scope: Literal["all", "mine"] = Query(default="mine"),
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, dict]:
    actor = authorize_job_action(job_id, scope, authorization, settings)
    try:
        job = set_admin_job_status(
            get_supabase_client(),
            job_id,
            new_status=payload.new_status,
            reason=payload.reason,
            changed_by_line_user_id=payload.changed_by_line_user_id or actor.get("line_user_id"),
            changed_by_name=payload.changed_by_name or actor.get("display_name"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update job status",
        ) from exc

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return {"job": job}


@router.post("/{job_id}/verify")
def verify_job(
    job_id: str,
    scope: Literal["all", "mine"] = Query(default="mine"),
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, dict]:
    authorize_job_action(job_id, scope, authorization, settings)
    try:
        job = verify_admin_job(get_supabase_client(), job_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify job",
        ) from exc

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return {"job": job}


@router.post("/{job_id}/hide")
def hide_job(
    job_id: str,
    scope: Literal["all", "mine"] = Query(default="mine"),
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, dict]:
    authorize_job_action(job_id, scope, authorization, settings)
    try:
        job = hide_admin_job(get_supabase_client(), job_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to hide job",
        ) from exc

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return {"job": job}


def authorize_job_action(
    job_id: str,
    scope: Literal["all", "mine"],
    authorization: Optional[str],
    settings: Settings,
) -> dict[str, str | None]:
    if scope != "mine":
        return {"line_user_id": None, "display_name": None}

    try:
        auth_result = verify_line_id_token(settings, bearer_token(authorization))
    except LineAuthError as exc:
        logger.info(
            "Admin job authorization failed endpoint=/admin/jobs scope=mine job_id=%s reason=line_auth_failed has_authorization=%s",
            job_id,
            bool(authorization),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LINEログイン確認に失敗しました",
        ) from exc

    job = fetch_admin_job_by_id(get_supabase_client(), job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    owner_match = job.get("created_by_line_user_id") == auth_result["line_user_id"]
    logger.info(
        "Admin job authorization checked endpoint=/admin/jobs scope=mine job_id=%s owner_match=%s has_authorization=%s",
        job_id,
        owner_match,
        bool(authorization),
    )
    if not owner_match:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自分の投稿のみ操作できます",
        )

    return auth_result
