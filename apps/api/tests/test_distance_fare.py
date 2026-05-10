from __future__ import annotations

import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-line-channel-secret")

from apps.api.app.core.config import get_settings  # noqa: E402
from apps.api.app.main import app  # noqa: E402
from apps.api.app.schemas.distance import DistanceMeasureRequest  # noqa: E402
from apps.api.app.services.distance import measure_driving_distance  # noqa: E402
from apps.api.app.services.fare_estimator import (  # noqa: E402
    classify_truck_vehicle,
    detect_transport_region,
    estimate_fare_for_job,
    estimate_standard_fare,
    fare_judgement,
    kei_cargo_standard_fare,
    round_distance_band,
)


class DistanceFareTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_kei_cargo_fare_for_92km_is_13850(self) -> None:
        self.assertEqual(kei_cargo_standard_fare(92), 13850)

    def test_kei_cargo_fare_for_155km_is_21650(self) -> None:
        self.assertEqual(kei_cargo_standard_fare(155), 21650)

    def test_kei_van_uses_kei_cargo_fare_and_ratio(self) -> None:
        result = estimate_standard_fare(distance_km=92, vehicle_type="軽バン", posted_fare="17000")

        self.assertEqual(result["standard_fare_yen"], 13850)
        self.assertEqual(result["fare_vehicle_class"], "kei_cargo")
        self.assertEqual(result["fare_vehicle_label"], "貨物軽自動車")
        self.assertEqual(result["fare_ratio_percent"], 122.7)
        self.assertEqual(result["fare_ratio_text"], "123%")
        self.assertEqual(result["fare_judgement"], "やや高い")
        self.assertEqual(result["fare_calc_status"], "ok")

    def test_kei_van_155km_ratio_is_slightly_cheap(self) -> None:
        result = estimate_standard_fare(distance_km=155, vehicle_type="軽バン", posted_fare="17000")

        self.assertEqual(result["standard_fare_yen"], 21650)
        self.assertEqual(result["fare_ratio_percent"], 78.5)
        self.assertEqual(result["fare_judgement"], "やや安い")

    def test_refrigerated_kei_cargo_uses_kei_fare_table(self) -> None:
        refrigerated = estimate_standard_fare(distance_km=155, vehicle_type="冷蔵軽貨物", posted_fare="17000")
        frozen = estimate_standard_fare(distance_km=155, vehicle_type="冷凍軽貨物", posted_fare="17000")

        self.assertEqual(refrigerated["fare_vehicle_class"], "kei_cargo")
        self.assertEqual(refrigerated["fare_vehicle_label"], "貨物軽自動車")
        self.assertEqual(refrigerated["standard_fare_yen"], 21650)
        self.assertIn("追加条件は含みません", refrigerated["fare_calc_note"])
        self.assertEqual(frozen["fare_vehicle_class"], "kei_cargo")
        self.assertEqual(frozen["standard_fare_yen"], 21650)

    def test_regular_kei_van_keeps_standard_kei_note(self) -> None:
        result = estimate_standard_fare(distance_km=155, vehicle_type="軽バン", posted_fare="17000")

        self.assertEqual(result["fare_calc_note"], "貨物軽自動車運送事業運賃料金表により計算")

    def test_truck_vehicle_classification(self) -> None:
        self.assertEqual(classify_truck_vehicle("2t"), "small_2t")
        self.assertEqual(classify_truck_vehicle("2トン"), "small_2t")
        self.assertEqual(classify_truck_vehicle("小型車"), "small_2t")
        self.assertEqual(classify_truck_vehicle("4t"), "medium_4t")
        self.assertEqual(classify_truck_vehicle("中型"), "medium_4t")
        self.assertEqual(classify_truck_vehicle("10t"), "large_10t")
        self.assertEqual(classify_truck_vehicle("大型車"), "large_10t")
        self.assertEqual(classify_truck_vehicle("トレーラー"), "trailer_20t")
        self.assertEqual(classify_truck_vehicle("20t trailer"), "trailer_20t")
        self.assertEqual(classify_truck_vehicle("1t"), "small_2t")

    def test_1t_falls_back_to_2t_class_with_estimated_note(self) -> None:
        result = estimate_fare_for_job(
            distance_km=154.9,
            vehicle_type="1t",
            pickup_prefecture="高知県",
            posted_fare="50000",
        )

        self.assertEqual(result["fare_vehicle_class"], "small_2t")
        self.assertEqual(result["fare_vehicle_label"], "小型車(2tクラス)")
        self.assertEqual(result["fare_calc_status"], "estimated")
        self.assertIn("1tは標準運賃表に独立区分がないため", result["fare_calc_note"])
        self.assertEqual(result["standard_fare_yen"], 40310)

    def test_transport_region_detection(self) -> None:
        self.assertEqual(detect_transport_region("愛媛県"), "shikoku")
        self.assertEqual(detect_transport_region("高知県高知市"), "shikoku")
        self.assertEqual(detect_transport_region("広島県"), "chugoku")
        self.assertEqual(detect_transport_region("福岡県"), "kyushu")
        self.assertEqual(detect_transport_region("東京都"), "kanto")

    def test_standard_truck_fare_uses_2024_table(self) -> None:
        result = estimate_fare_for_job(
            distance_km=154.9,
            vehicle_type="2t",
            pickup_prefecture="高知県",
            posted_fare="50000",
        )

        self.assertEqual(result["fare_vehicle_class"], "small_2t")
        self.assertEqual(result["fare_vehicle_label"], "小型車(2tクラス)")
        self.assertEqual(result["fare_region"], "shikoku")
        self.assertEqual(result["standard_fare_yen"], 40310)
        self.assertEqual(result["fare_calc_status"], "ok")

    def test_standard_table_missing_is_safe(self) -> None:
        result = estimate_fare_for_job(
            distance_km=154.9,
            vehicle_type="2t",
            pickup_prefecture="北海道",
            posted_fare="50000",
        )

        self.assertIsNone(result["standard_fare_yen"])
        self.assertIsNone(result["fare_ratio_percent"])
        self.assertEqual(result["fare_region"], "hokkaido")
        self.assertEqual(result["fare_calc_status"], "standard_table_missing")

    def test_unknown_vehicle_is_safe(self) -> None:
        result = estimate_fare_for_job(
            distance_km=154.9,
            vehicle_type="その他",
            pickup_prefecture="高知県",
            posted_fare="50000",
        )

        self.assertIsNone(result["standard_fare_yen"])
        self.assertEqual(result["fare_calc_status"], "vehicle_unknown")

    def test_price_or_fare_can_be_used_for_comparison(self) -> None:
        price_result = estimate_fare_for_job(
            distance_km=155,
            vehicle_type="軽バン",
            price="１７，０００円",
            pickup_prefecture="高知県",
        )
        fare_result = estimate_fare_for_job(
            distance_km=155,
            vehicle_type="軽バン",
            fare="¥17000",
            pickup_prefecture="高知県",
        )

        self.assertEqual(price_result["posted_fare_yen"], 17000)
        self.assertEqual(fare_result["posted_fare_yen"], 17000)
        self.assertEqual(price_result["fare_ratio_percent"], 78.5)

    def test_truck_distance_band_rounds_up(self) -> None:
        self.assertEqual(round_distance_band(100.1, table_bands=list(range(10, 210, 10))), 110)
        self.assertEqual(round_distance_band(154.9, table_bands=list(range(10, 210, 10))), 160)

    def test_distance_request_uses_price_or_fare_as_posted_fare(self) -> None:
        price_payload = DistanceMeasureRequest(
            pickup_address="高知県高知市",
            delivery_address="愛媛県松山市",
            vehicle_type="軽バン",
            price="17000",
        )
        fare_payload = DistanceMeasureRequest(
            pickup_address="高知県高知市",
            delivery_address="愛媛県松山市",
            vehicle_type="軽バン",
            fare="18000",
        )

        self.assertEqual(price_payload.effective_posted_fare(), "17000")
        self.assertEqual(fare_payload.effective_posted_fare(), "18000")

    def test_fare_judgement_labels(self) -> None:
        self.assertEqual(fare_judgement(69.9), "かなり安い")
        self.assertEqual(fare_judgement(70), "やや安い")
        self.assertEqual(fare_judgement(78.5), "やや安い")
        self.assertEqual(fare_judgement(89.9), "やや安い")
        self.assertEqual(fare_judgement(90), "標準付近")
        self.assertEqual(fare_judgement(110), "標準付近")
        self.assertEqual(fare_judgement(110.1), "やや高い")
        self.assertEqual(fare_judgement(130), "やや高い")
        self.assertEqual(fare_judgement(130.1), "高い")

    def test_distance_api_key_missing_returns_safe_response(self) -> None:
        settings = SimpleNamespace(maps_api_key=None)

        result = measure_driving_distance(
            settings=settings,
            pickup_address="高知県高知市高知",
            delivery_address="愛媛県松山市",
            vehicle_type="軽バン",
            posted_fare="17000",
            detail_address_missing=True,
        )

        self.assertIsNone(result["distance_km"])
        self.assertEqual(result["fare_calc_status"], "api_key_missing")
        self.assertIn("距離取得APIが設定されていません", result["fare_calc_note"])
        self.assertIn("市区町村単位での概算距離", result["fare_calc_note"])

    def test_distance_note_marks_city_level_estimate_when_detail_missing(self) -> None:
        settings = SimpleNamespace(maps_api_key="dummy")

        with patch("apps.api.app.services.distance.fetch_google_driving_distance_km", return_value=154.9):
            result = measure_driving_distance(
                settings=settings,
                pickup_address="高知県高知市",
                delivery_address="愛媛県松山市",
                vehicle_type="軽バン",
                posted_fare="17000",
                detail_address_missing=True,
            )

        self.assertEqual(result["fare_calc_status"], "ok")
        self.assertIn("市区町村単位での概算距離", result["fare_calc_note"])

    def test_distance_measure_route_response_format(self) -> None:
        app.dependency_overrides[get_settings] = lambda: SimpleNamespace(maps_api_key=None)

        response = self.client.post(
            "/distance/measure",
            json={
                "pickup_address": "高知県高知市高知",
                "delivery_address": "愛媛県松山市",
                "vehicle_type": "軽バン",
                "posted_fare": "17000",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("distance_km", data)
        self.assertIn("distance_text", data)
        self.assertIn("standard_fare_yen", data)
        self.assertIn("fare_ratio_percent", data)
        self.assertEqual(data["fare_calc_status"], "api_key_missing")

    def test_distance_measure_route_calculates_truck_from_table(self) -> None:
        app.dependency_overrides[get_settings] = lambda: SimpleNamespace(maps_api_key="dummy")

        with patch("apps.api.app.services.distance.fetch_google_driving_distance_km", return_value=154.9):
            response = self.client.post(
                "/distance/measure",
                json={
                    "pickup_address": "高知県高知市",
                    "delivery_address": "愛媛県松山市",
                    "pickup_prefecture": "高知県",
                    "vehicle_type": "2t",
                    "posted_fare": "50000",
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["fare_vehicle_class"], "small_2t")
        self.assertEqual(data["fare_region"], "shikoku")
        self.assertEqual(data["standard_fare_yen"], 40310)
        self.assertEqual(data["fare_calc_status"], "ok")

    def test_frontend_vehicle_dropdown_options_do_not_include_1t(self) -> None:
        constants_path = Path(__file__).resolve().parents[3] / "apps" / "web" / "src" / "constants" / "vehicleTypes.ts"
        source = constants_path.read_text(encoding="utf-8")

        for option in ["軽バン", "冷蔵軽貨物", "2t", "4t", "10t", "トレーラー", "その他"]:
            self.assertIn(f'"{option}"', source)
        self.assertNotIn('"1t"', source)


if __name__ == "__main__":
    unittest.main()
