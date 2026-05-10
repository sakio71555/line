from __future__ import annotations

from typing import Any, Optional

import httpx

from ..core.config import Settings
from .fare_estimator import estimate_standard_fare

GOOGLE_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


def measure_driving_distance(
    *,
    settings: Settings,
    pickup_address: str,
    delivery_address: str,
    vehicle_type: Optional[str],
    posted_fare: object = None,
    pickup_prefecture: Optional[str] = None,
    detail_address_missing: bool = False,
) -> dict[str, Any]:
    if not settings.maps_api_key:
        return distance_response(
            distance_km=None,
            distance_source=None,
            vehicle_type=vehicle_type,
            posted_fare=posted_fare,
            pickup_prefecture=pickup_prefecture or pickup_address,
            status="api_key_missing",
            note="距離取得APIが設定されていません",
            detail_address_missing=detail_address_missing,
        )

    try:
        distance_km = fetch_google_driving_distance_km(
            settings.maps_api_key,
            pickup_address=pickup_address,
            delivery_address=delivery_address,
        )
    except DistanceMeasureError as exc:
        return distance_response(
            distance_km=None,
            distance_source="google_maps",
            vehicle_type=vehicle_type,
            posted_fare=posted_fare,
            pickup_prefecture=pickup_prefecture or pickup_address,
            status=exc.status,
            note=exc.safe_note,
            detail_address_missing=detail_address_missing,
        )

    return distance_response(
        distance_km=distance_km,
        distance_source="google_maps",
        vehicle_type=vehicle_type,
        posted_fare=posted_fare,
        pickup_prefecture=pickup_prefecture or pickup_address,
        status=None,
        note=None,
        detail_address_missing=detail_address_missing,
    )


def fetch_google_driving_distance_km(
    api_key: str,
    *,
    pickup_address: str,
    delivery_address: str,
) -> float:
    try:
        response = httpx.get(
            GOOGLE_DISTANCE_MATRIX_URL,
            params={
                "origins": pickup_address,
                "destinations": delivery_address,
                "mode": "driving",
                "language": "ja",
                "units": "metric",
                "key": api_key,
            },
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DistanceMeasureError("request_failed", "距離を取得できませんでした") from exc

    data = response.json()
    if data.get("status") != "OK":
        raise DistanceMeasureError("provider_error", "距離取得APIでエラーが発生しました")

    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        raise DistanceMeasureError("no_route", "住所を確認してください")
    elements = rows[0].get("elements") if isinstance(rows[0], dict) else None
    if not isinstance(elements, list) or not elements:
        raise DistanceMeasureError("no_route", "住所を確認してください")
    element = elements[0]
    if not isinstance(element, dict) or element.get("status") != "OK":
        raise DistanceMeasureError("no_route", "住所を確認してください")
    distance = element.get("distance")
    meters = distance.get("value") if isinstance(distance, dict) else None
    if not isinstance(meters, (int, float)):
        raise DistanceMeasureError("no_route", "住所を確認してください")

    return round(float(meters) / 1000, 1)


def distance_response(
    *,
    distance_km: Optional[float],
    distance_source: Optional[str],
    vehicle_type: Optional[str],
    posted_fare: object,
    pickup_prefecture: Optional[str],
    status: Optional[str],
    note: Optional[str],
    detail_address_missing: bool = False,
) -> dict[str, Any]:
    fare = estimate_standard_fare(
        distance_km=distance_km,
        vehicle_type=vehicle_type,
        posted_fare=posted_fare,
        pickup_prefecture=pickup_prefecture,
    )
    fare_status = status or fare["fare_calc_status"]
    fare_note = note or fare["fare_calc_note"]
    if detail_address_missing:
        fare_note = append_note(fare_note, "詳細住所が未入力のため、市区町村単位での概算距離です。")
    return {
        "distance_km": distance_km,
        "distance_text": distance_text(distance_km),
        "distance_source": distance_source,
        **fare,
        "fare_calc_status": fare_status,
        "fare_calc_note": fare_note,
    }


def append_note(note: Optional[str], addition: str) -> str:
    if note and addition in note:
        return note
    if note:
        return f"{note.rstrip('。')}。{addition}"
    return addition


def distance_text(distance_km: Optional[float]) -> Optional[str]:
    if distance_km is None:
        return None
    rounded = round(distance_km)
    return f"約{rounded}km"


class DistanceMeasureError(Exception):
    def __init__(self, status: str, safe_note: str) -> None:
        super().__init__(status)
        self.status = status
        self.safe_note = safe_note
