from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-line-channel-secret")

from apps.api.app.main import app  # noqa: E402
from apps.api.app.services.company_search import search_company_cards  # noqa: E402


class CompanySearchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_search_company_by_company_name(self) -> None:
        csv_path = self.write_company_csv()

        result = search_company_cards("四国物流", csv_path=csv_path)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["company"], "四国物流株式会社")
        self.assertEqual(result["items"][0]["name"], "山田 太郎")

    def test_search_phone_without_hyphens(self) -> None:
        csv_path = self.write_company_csv()

        result = search_company_cards("09012345678", csv_path=csv_path)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["mobile"], "090-1234-5678")

    def test_empty_query_returns_empty_items(self) -> None:
        response = self.client.get("/companies/search", params={"q": ""})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": [], "count": 0})

    def test_limit_caps_results(self) -> None:
        csv_path = self.write_company_csv(
            rows=[
                {"Company": "検索運送A", "Name": "山田 A", "Mobile": "090-1111-1111"},
                {"Company": "検索運送B", "Name": "山田 B", "Mobile": "090-2222-2222"},
            ]
        )

        result = search_company_cards("検索運送", limit=1, csv_path=csv_path)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["company"], "検索運送A")

    def test_missing_csv_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_path = Path(directory) / "missing-business-cards.csv"

            result = search_company_cards("四国", csv_path=missing_path)

        self.assertEqual(result["items"], [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["message"], "企業データCSVが見つかりません")

    def test_route_clamps_limit_to_maximum(self) -> None:
        with patch("apps.api.app.routers.companies.search_company_cards", return_value={"items": [], "count": 0}) as search:
            response = self.client.get("/companies/search", params={"q": "四国", "limit": 999})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args.kwargs["limit"], 100)

    def write_company_csv(self, rows: list[dict[str, str]] | None = None) -> Path:
        headers = [
            "Company",
            "Title",
            "Name",
            "NameRoman",
            "TEL",
            "Mobile",
            "FAX",
            "TollFree",
            "Email",
            "Postal",
            "Region",
            "Address1",
            "Branches",
            "Address3",
            "URL",
            "LineURL",
            "Notes",
        ]
        default_rows = [
            {
                "Company": "四国物流株式会社",
                "Title": "代表取締役",
                "Name": "山田 太郎",
                "NameRoman": "Taro Yamada",
                "TEL": "089-000-0000",
                "Mobile": "090-1234-5678",
                "FAX": "089-000-0001",
                "TollFree": "0120-000-000",
                "Email": "sample@example.com",
                "Postal": "790-0000",
                "Region": "四国",
                "Address1": "愛媛県松山市一番町1-1",
                "Branches": "高松支店",
                "Address3": "",
                "URL": "https://example.com",
                "LineURL": "",
                "Notes": "冷蔵対応",
            }
        ]
        directory = Path(tempfile.mkdtemp())
        csv_path = directory / "BusinessCards_Export.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            csv_file.write(",".join(headers) + "\n")
            for row in rows or default_rows:
                values = [row.get(header, "") for header in headers]
                csv_file.write(",".join(values) + "\n")
        return csv_path


if __name__ == "__main__":
    unittest.main()
