from __future__ import annotations

import math
from typing import Any, Optional

KEI_VEHICLE_KEYWORDS = {
    "軽バン",
    "軽貨物",
    "軽自動車",
    "軽トラ",
    "軽トラック",
    "軽",
    "kei",
    "kei van",
}


def estimate_standard_fare(
    *,
    distance_km: Optional[float],
    vehicle_type: Optional[str],
    posted_fare: object = None,
) -> dict[str, Any]:
    if distance_km is None:
        return fare_result(
            standard_fare_yen=None,
            vehicle_class=None,
            vehicle_label=None,
            status="distance_missing",
            note="走行距離が取得できていないため標準運賃を計算できません",
            posted_fare=posted_fare,
        )

    if is_kei_cargo(vehicle_type):
        standard_fare = kei_cargo_standard_fare(distance_km)
        return fare_result(
            standard_fare_yen=standard_fare,
            vehicle_class="kei_cargo",
            vehicle_label="貨物軽自動車",
            status="ok",
            note="貨物軽自動車運送事業運賃料金表により計算",
            posted_fare=posted_fare,
        )

    return fare_result(
        standard_fare_yen=None,
        vehicle_class=truck_vehicle_class(vehicle_type),
        vehicle_label=truck_vehicle_label(vehicle_type),
        status="unsupported_vehicle_class",
        note="通常トラックの標準運賃データが未設定のため未計算です",
        posted_fare=posted_fare,
    )


def is_kei_cargo(vehicle_type: Optional[str]) -> bool:
    if not vehicle_type:
        return False
    normalized = vehicle_type.strip().casefold()
    compact = normalized.replace(" ", "")
    return normalized in KEI_VEHICLE_KEYWORDS or compact in {keyword.replace(" ", "") for keyword in KEI_VEHICLE_KEYWORDS}


def kei_cargo_standard_fare(distance_km: float) -> int:
    if distance_km <= 0:
        return 0
    if distance_km <= 50:
        return math.ceil(distance_km / 10) * 1600
    return 8000 + math.ceil((distance_km - 50) / 5) * 650


def fare_result(
    *,
    standard_fare_yen: Optional[int],
    vehicle_class: Optional[str],
    vehicle_label: Optional[str],
    status: str,
    note: str,
    posted_fare: object,
) -> dict[str, Any]:
    parsed_posted_fare = parse_posted_fare(posted_fare)
    ratio = fare_ratio_percent(parsed_posted_fare, standard_fare_yen)
    return {
        "standard_fare_yen": standard_fare_yen,
        "fare_ratio_percent": ratio,
        "fare_ratio_text": f"{round(ratio):.0f}%" if ratio is not None else None,
        "fare_judgement": fare_judgement(ratio),
        "fare_vehicle_class": vehicle_class,
        "fare_vehicle_label": vehicle_label,
        "fare_calc_status": status,
        "fare_calc_note": note,
    }


def parse_posted_fare(value: object) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = "".join(char for char in value if char.isdigit())
        return int(digits) if digits else None
    return None


def fare_ratio_percent(posted_fare: Optional[int], standard_fare_yen: Optional[int]) -> Optional[float]:
    if posted_fare is None or not standard_fare_yen:
        return None
    return round(posted_fare / standard_fare_yen * 100, 1)


def fare_judgement(ratio: Optional[float]) -> Optional[str]:
    if ratio is None:
        return None
    if ratio < 70:
        return "かなり安い"
    if ratio < 90:
        return "やや安い"
    if ratio <= 110:
        return "標準付近"
    if ratio <= 130:
        return "やや高い"
    return "高い"


def truck_vehicle_class(vehicle_type: Optional[str]) -> Optional[str]:
    if not vehicle_type:
        return None
    normalized = vehicle_type.strip().casefold()
    if any(keyword in normalized for keyword in ["10t", "10トン", "大型"]):
        return "large_truck"
    if any(keyword in normalized for keyword in ["4t", "4トン", "中型"]):
        return "medium_truck"
    if any(keyword in normalized for keyword in ["1t", "2t", "1トン", "2トン", "小型"]):
        return "small_truck"
    if "トレーラー" in normalized or "trailer" in normalized:
        return "trailer"
    return "unknown"


def truck_vehicle_label(vehicle_type: Optional[str]) -> Optional[str]:
    vehicle_class = truck_vehicle_class(vehicle_type)
    return {
        "small_truck": "小型車",
        "medium_truck": "中型車",
        "large_truck": "大型車",
        "trailer": "トレーラー",
        "unknown": "車種区分未判定",
        None: None,
    }[vehicle_class]
