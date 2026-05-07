from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..services.supabase import fetch_admin_line_messages, get_supabase_client

router = APIRouter(prefix="/admin/line-messages", tags=["admin-line-messages"])


@router.get("")
def list_admin_line_messages() -> dict[str, list[dict]]:
    try:
        line_messages = fetch_admin_line_messages(get_supabase_client())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch line messages",
        ) from exc

    return {"line_messages": line_messages}
