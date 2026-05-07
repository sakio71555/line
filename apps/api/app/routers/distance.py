from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.config import Settings, get_settings
from ..schemas.distance import DistanceMeasureRequest
from ..services.distance import measure_driving_distance

router = APIRouter(prefix="/distance", tags=["distance"])


@router.post("/measure")
def measure_distance(payload: DistanceMeasureRequest, settings: Settings = Depends(get_settings)) -> dict:
    return measure_driving_distance(
        settings=settings,
        pickup_address=payload.pickup_address,
        delivery_address=payload.delivery_address,
        vehicle_type=payload.vehicle_type,
        posted_fare=payload.posted_fare,
    )

