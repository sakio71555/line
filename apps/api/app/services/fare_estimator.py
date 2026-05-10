from __future__ import annotations

import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

KEI_VEHICLE_KEYWORDS = {
    "軽バン",
    "軽貨物",
    "冷蔵軽貨物",
    "冷凍軽貨物",
    "軽自動車",
    "軽トラ",
    "軽トラック",
    "軽",
    "kei",
    "kei van",
}

TRUCK_VEHICLE_CLASSES = {
    "small_2t": "小型車(2tクラス)",
    "medium_4t": "中型車(4tクラス)",
    "large_10t": "大型車(10tクラス)",
    "trailer_20t": "トレーラー(20tクラス)",
}

TRANSPORT_REGIONS = {
    "hokkaido": {"北海道"},
    "tohoku": {"青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県"},
    "hokuriku_shinetsu": {"新潟県", "富山県", "石川県", "長野県"},
    "kanto": {"東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県", "山梨県"},
    "chubu": {"岐阜県", "静岡県", "愛知県", "三重県", "福井県"},
    "kinki": {"大阪府", "京都府", "兵庫県", "奈良県", "滋賀県", "和歌山県"},
    "chugoku": {"鳥取県", "島根県", "岡山県", "広島県", "山口県"},
    "shikoku": {"徳島県", "香川県", "愛媛県", "高知県"},
    "kyushu": {"福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県"},
    "okinawa": {"沖縄県"},
}

FARE_DATA_PATH = Path(__file__).resolve().parents[4] / "data" / "standard_truck_fares_2024.json"


def estimate_standard_fare(
    *,
    distance_km: Optional[float],
    vehicle_type: Optional[str],
    posted_fare: object = None,
    pickup_prefecture: Optional[str] = None,
) -> dict[str, Any]:
    return estimate_fare_for_job(
        distance_km=distance_km,
        vehicle_type=vehicle_type,
        posted_fare=posted_fare,
        pickup_prefecture=pickup_prefecture,
    )


def estimate_fare_for_job(
    *,
    distance_km: Optional[float],
    vehicle_type: Optional[str],
    posted_fare: object = None,
    fare: object = None,
    price: object = None,
    pickup_prefecture: Optional[str] = None,
) -> dict[str, Any]:
    posted_fare_yen = parse_posted_fare(posted_fare if posted_fare is not None else price if price is not None else fare)

    if distance_km is None:
        return fare_result(
            posted_fare_yen=posted_fare_yen,
            standard_fare_yen=None,
            vehicle_class=None,
            vehicle_label=None,
            region=detect_transport_region(pickup_prefecture),
            status="distance_missing",
            note="走行距離が取得できていないため標準運賃を計算できません",
        )

    if is_kei_cargo_vehicle(vehicle_type):
        note = (
            "冷蔵・冷凍軽貨物は貨物軽自動車運賃表をもとに概算しています。"
            "冷蔵・冷凍設備等の追加条件は含みません。"
            if is_refrigerated_kei_cargo_vehicle(vehicle_type)
            else "貨物軽自動車運送事業運賃料金表により計算"
        )
        return fare_result(
            posted_fare_yen=posted_fare_yen,
            standard_fare_yen=estimate_kei_cargo_fare(distance_km),
            vehicle_class="kei_cargo",
            vehicle_label="貨物軽自動車",
            region=detect_transport_region(pickup_prefecture),
            status="ok",
            note=note,
        )

    vehicle_class = classify_truck_vehicle(vehicle_type)
    if not vehicle_class:
        return fare_result(
            posted_fare_yen=posted_fare_yen,
            standard_fare_yen=None,
            vehicle_class=None,
            vehicle_label=None,
            region=detect_transport_region(pickup_prefecture),
            status="vehicle_unknown",
            note="車種区分を判定できませんでした",
        )

    one_t_fallback = is_one_t_vehicle(vehicle_type)
    return estimate_standard_truck_fare(
        distance_km=distance_km,
        vehicle_class=vehicle_class,
        pickup_prefecture=pickup_prefecture,
        posted_fare_yen=posted_fare_yen,
        calc_status="estimated" if one_t_fallback else "ok",
        calc_note="1tは標準運賃表に独立区分がないため、小型車(2tクラス)として概算"
        if one_t_fallback
        else "令和6年3月告示の標準的な運賃により計算",
    )


def is_kei_cargo_vehicle(vehicle_type: Optional[str]) -> bool:
    if not vehicle_type:
        return False
    normalized = normalize_text(vehicle_type)
    compact = normalized.replace(" ", "")
    normalized_keywords = {normalize_text(keyword) for keyword in KEI_VEHICLE_KEYWORDS}
    compact_keywords = {keyword.replace(" ", "") for keyword in normalized_keywords}
    return (
        normalized in normalized_keywords
        or compact in compact_keywords
        or any(keyword != "軽" and keyword in normalized for keyword in normalized_keywords)
    )


def is_refrigerated_kei_cargo_vehicle(vehicle_type: Optional[str]) -> bool:
    if not vehicle_type:
        return False
    normalized = normalize_text(vehicle_type)
    return any(keyword in normalized for keyword in ["冷蔵", "冷凍", "チルド"])


def estimate_kei_cargo_fare(distance_km: float) -> int:
    if distance_km <= 0:
        return 0
    if distance_km <= 50:
        return math.ceil(distance_km / 10) * 1600
    return 8000 + math.ceil((distance_km - 50) / 5) * 650


def classify_truck_vehicle(vehicle_type: Optional[str]) -> Optional[str]:
    if not vehicle_type:
        return None
    normalized = normalize_text(vehicle_type)
    compact = normalized.replace(" ", "")
    if any(keyword in normalized for keyword in ["トレーラー", "trailer"]) or "20t" in compact or "20トン" in compact:
        return "trailer_20t"
    if "10t" in compact or "10トン" in compact or any(keyword in normalized for keyword in ["大型", "大型車"]):
        return "large_10t"
    if "4t" in compact or "4トン" in compact or any(keyword in normalized for keyword in ["中型", "中型車"]):
        return "medium_4t"
    if "2t" in compact or "2トン" in compact or any(keyword in normalized for keyword in ["小型", "小型車"]):
        return "small_2t"
    if is_one_t_vehicle(vehicle_type):
        return "small_2t"
    return None


def is_one_t_vehicle(vehicle_type: Optional[str]) -> bool:
    if not vehicle_type:
        return False
    compact = normalize_text(vehicle_type).replace(" ", "")
    return "1t" in compact or "1トン" in compact


def detect_transport_region(prefecture: Optional[str]) -> Optional[str]:
    if not prefecture:
        return None
    normalized = unicodedata.normalize("NFKC", prefecture)
    for region, prefectures in TRANSPORT_REGIONS.items():
        if any(prefecture_name in normalized for prefecture_name in prefectures):
            return region
    return None


def estimate_standard_truck_fare(
    *,
    distance_km: float,
    vehicle_class: str,
    pickup_prefecture: Optional[str],
    posted_fare_yen: Optional[int],
    calc_status: str = "ok",
    calc_note: str = "令和6年3月告示の標準的な運賃により計算",
) -> dict[str, Any]:
    region = detect_transport_region(pickup_prefecture)
    vehicle_label = TRUCK_VEHICLE_CLASSES.get(vehicle_class)
    fare_data = load_standard_truck_fares().get("distance_based_fares", {})
    region_table = fare_data.get(region) if region else None
    if not isinstance(region_table, dict):
        return fare_result(
            posted_fare_yen=posted_fare_yen,
            standard_fare_yen=None,
            vehicle_class=vehicle_class,
            vehicle_label=vehicle_label,
            region=region,
            status="standard_table_missing",
            note="標準運賃表データが未登録です",
        )

    standard_fare_yen = standard_truck_fare_from_table(region_table, distance_km, vehicle_class)
    if standard_fare_yen is None:
        return fare_result(
            posted_fare_yen=posted_fare_yen,
            standard_fare_yen=None,
            vehicle_class=vehicle_class,
            vehicle_label=vehicle_label,
            region=region,
            status="standard_table_missing",
            note="標準運賃表データが未登録です",
        )

    return fare_result(
        posted_fare_yen=posted_fare_yen,
        standard_fare_yen=standard_fare_yen,
        vehicle_class=vehicle_class,
        vehicle_label=vehicle_label,
        region=region,
        status=calc_status,
        note=calc_note,
    )


def standard_truck_fare_from_table(
    region_table: dict[str, Any],
    distance_km: float,
    vehicle_class: str,
) -> Optional[int]:
    fares_by_km = region_table.get("fares_by_km")
    if not isinstance(fares_by_km, dict):
        return None

    band = round_distance_band(distance_km, table_bands=[int(key) for key in fares_by_km.keys()])
    if band <= 200:
        row = fares_by_km.get(str(band))
        value = row.get(vehicle_class) if isinstance(row, dict) else None
        return int(value) if isinstance(value, int) else None

    base_row = fares_by_km.get("200")
    base_value = base_row.get(vehicle_class) if isinstance(base_row, dict) else None
    if not isinstance(base_value, int):
        return None

    if band <= 500:
        increment = (region_table.get("over_200_increment_20km") or {}).get(vehicle_class)
        steps = math.ceil((band - 200) / 20)
    else:
        over_200_increment = (region_table.get("over_200_increment_20km") or {}).get(vehicle_class)
        over_500_increment = (region_table.get("over_500_increment_50km") or {}).get(vehicle_class)
        if not isinstance(over_200_increment, int) or not isinstance(over_500_increment, int):
            return None
        base_value += math.ceil((500 - 200) / 20) * over_200_increment
        increment = over_500_increment
        steps = math.ceil((band - 500) / 50)

    if not isinstance(increment, int):
        return None
    return base_value + steps * increment


def round_distance_band(distance_km: float, *, table_bands: list[int]) -> int:
    if distance_km <= 0:
        return min(table_bands)
    if distance_km <= 200:
        candidates = sorted(band for band in table_bands if band >= distance_km)
        return candidates[0] if candidates else 200
    if distance_km <= 500:
        return 200 + math.ceil((distance_km - 200) / 20) * 20
    return 500 + math.ceil((distance_km - 500) / 50) * 50


def compare_posted_fare(
    posted_fare: object,
    standard_fare_yen: Optional[int],
) -> dict[str, Any]:
    posted_fare_yen = parse_posted_fare(posted_fare)
    ratio = fare_ratio_percent(posted_fare_yen, standard_fare_yen)
    return {
        "posted_fare_yen": posted_fare_yen,
        "fare_ratio_percent": ratio,
        "fare_ratio_text": f"{round(ratio):.0f}%" if ratio is not None else None,
        "fare_judgement": fare_judgement(ratio),
    }


def fare_result(
    *,
    posted_fare_yen: Optional[int],
    standard_fare_yen: Optional[int],
    vehicle_class: Optional[str],
    vehicle_label: Optional[str],
    region: Optional[str],
    status: str,
    note: str,
) -> dict[str, Any]:
    comparison = compare_posted_fare(posted_fare_yen, standard_fare_yen)
    return {
        "posted_fare_yen": posted_fare_yen,
        "standard_fare_yen": standard_fare_yen,
        "fare_ratio_percent": comparison["fare_ratio_percent"],
        "fare_ratio_text": comparison["fare_ratio_text"],
        "fare_judgement": comparison["fare_judgement"],
        "fare_vehicle_class": vehicle_class,
        "fare_vehicle_label": vehicle_label,
        "fare_region": region,
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
        normalized = unicodedata.normalize("NFKC", value)
        digits = "".join(char for char in normalized if char.isdigit())
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


@lru_cache
def load_standard_truck_fares() -> dict[str, Any]:
    try:
        with FARE_DATA_PATH.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {"metadata": {}, "distance_based_fares": {}}


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


# Backward-compatible names used by existing tests and callers.
def is_kei_cargo(vehicle_type: Optional[str]) -> bool:
    return is_kei_cargo_vehicle(vehicle_type)


def kei_cargo_standard_fare(distance_km: float) -> int:
    return estimate_kei_cargo_fare(distance_km)
