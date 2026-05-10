from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FARE_JSON = ROOT / "data" / "standard_truck_fares_2024.json"
REGIONS = ("shikoku", "chugoku", "kyushu", "kinki", "kanto")
VEHICLE_CLASSES = ("small_2t", "medium_4t", "large_10t", "trailer_20t")


class StandardTruckFaresJsonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(FARE_JSON.read_text(encoding="utf-8"))

    def test_json_has_expected_top_level_structure(self) -> None:
        self.assertIn("metadata", self.data)
        self.assertIn("distance_based_fares", self.data)
        self.assertEqual(self.data["metadata"]["version"], "令和6年3月告示")

    def test_supported_regions_have_fares_by_km_and_vehicle_classes(self) -> None:
        regions = self.data["distance_based_fares"]
        for region in REGIONS:
            self.assertIn(region, regions)
            fares_by_km = regions[region].get("fares_by_km")
            self.assertIsInstance(fares_by_km, dict)
            distance_keys = [int(key) for key in fares_by_km.keys()]
            self.assertEqual(distance_keys, sorted(distance_keys))
            for row in fares_by_km.values():
                for vehicle_class in VEHICLE_CLASSES:
                    self.assertIn(vehicle_class, row)
                    self.assertIsInstance(row[vehicle_class], int)

    def test_representative_values_are_readable(self) -> None:
        fares = self.data["distance_based_fares"]
        samples = [
            ("shikoku", "100", "small_2t"),
            ("shikoku", "150", "small_2t"),
            ("shikoku", "100", "medium_4t"),
            ("chugoku", "100", "small_2t"),
            ("kanto", "100", "small_2t"),
        ]
        for region, distance, vehicle_class in samples:
            with self.subTest(region=region, distance=distance, vehicle_class=vehicle_class):
                value = fares[region]["fares_by_km"][distance][vehicle_class]
                self.assertGreater(value, 0)


if __name__ == "__main__":
    unittest.main()
