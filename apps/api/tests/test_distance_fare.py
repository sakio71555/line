from __future__ import annotations

import os
import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-line-channel-secret")

from apps.api.app.core.config import get_settings  # noqa: E402
from apps.api.app.main import app  # noqa: E402
from apps.api.app.services.distance import measure_driving_distance  # noqa: E402
from apps.api.app.services.fare_estimator import estimate_standard_fare, fare_judgement, kei_cargo_standard_fare  # noqa: E402


class DistanceFareTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_kei_cargo_fare_for_92km_is_13850(self) -> None:
        self.assertEqual(kei_cargo_standard_fare(92), 13850)

    def test_kei_van_uses_kei_cargo_fare_and_ratio(self) -> None:
        result = estimate_standard_fare(distance_km=92, vehicle_type="軽バン", posted_fare="17000")

        self.assertEqual(result["standard_fare_yen"], 13850)
        self.assertEqual(result["fare_vehicle_class"], "kei_cargo")
        self.assertEqual(result["fare_vehicle_label"], "貨物軽自動車")
        self.assertEqual(result["fare_ratio_percent"], 122.7)
        self.assertEqual(result["fare_ratio_text"], "123%")
        self.assertEqual(result["fare_judgement"], "やや高い")
        self.assertEqual(result["fare_calc_status"], "ok")

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
        )

        self.assertIsNone(result["distance_km"])
        self.assertEqual(result["fare_calc_status"], "api_key_missing")
        self.assertEqual(result["fare_calc_note"], "距離取得APIが設定されていません")

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


if __name__ == "__main__":
    unittest.main()
