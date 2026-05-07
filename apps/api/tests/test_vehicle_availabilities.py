from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-line-channel-secret")

from apps.api.app.main import app  # noqa: E402
from apps.api.app.services.supabase import SupabaseRestClient, fetch_vehicle_availabilities  # noqa: E402


class VehicleAvailabilitiesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_vehicle_availabilities_route_returns_rows(self) -> None:
        rows = [
            {
                "id": "vehicle-1",
                "location": "愛媛県 松山市",
                "vehicle_type": "軽バン",
                "status": "open",
                "created_at": "2026-05-07T10:00:00+09:00",
            }
        ]

        with patch("apps.api.app.routers.vehicle_availabilities.get_supabase_client", return_value=object()), patch(
            "apps.api.app.routers.vehicle_availabilities.fetch_vehicle_availabilities",
            return_value=rows,
        ):
            response = self.client.get("/vehicle-availabilities")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"vehicle_availabilities": rows})

    def test_fetch_vehicle_availabilities_uses_open_status_and_newest_order(self) -> None:
        client = SupabaseRestClient("https://example.supabase.co", "test-key")
        request = httpx.Request("GET", "https://example.supabase.co/rest/v1/vehicle_availabilities")
        response = httpx.Response(200, json=[], request=request)

        with patch("apps.api.app.services.supabase.httpx.get", return_value=response) as get:
            rows = fetch_vehicle_availabilities(client, limit=999)

        self.assertEqual(rows, [])
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["status"], "eq.open")
        self.assertEqual(params["order"], "created_at.desc")
        self.assertEqual(params["limit"], "200")


if __name__ == "__main__":
    unittest.main()

