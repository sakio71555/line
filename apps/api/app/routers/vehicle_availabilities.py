from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ..services.supabase import fetch_vehicle_availabilities, get_supabase_client

router = APIRouter(prefix="/vehicle-availabilities", tags=["vehicle-availabilities"])


@router.get("")
def list_vehicle_availabilities(limit: int = Query(default=100, ge=1, le=200)) -> dict[str, list[dict]]:
    try:
        vehicle_availabilities = fetch_vehicle_availabilities(get_supabase_client(), limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch vehicle availabilities",
        ) from exc

    return {"vehicle_availabilities": vehicle_availabilities}

