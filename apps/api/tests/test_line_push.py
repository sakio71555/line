from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from apps.api.app.services.line_push import build_liff_job_created_text, push_liff_job_created_message, push_menu_message


class LinePushTest(unittest.TestCase):
    def test_build_liff_job_created_text_announces_public_job(self) -> None:
        text = build_liff_job_created_text(
            {
                "pickup_location": "大阪府 大阪市",
                "delivery_location": "埼玉県 日高市",
                "job_category": "spot",
                "vehicle_type": "4t",
                "price": 8000,
                "distance_text": "約92km",
                "standard_fare_yen": 13850,
                "fare_ratio_percent": 122.7,
                "fare_judgement": "やや高い",
                "company_name": "テスト運送",
                "contact_name": "山田",
                "phone_number": "090-1234-5678",
            }
        )

        self.assertIn("新規案件が投稿されました", text)
        self.assertIn("【案件種別】\nスポット便", text)
        self.assertIn("【区間】", text)
        self.assertIn("大阪府 大阪市 → 埼玉県 日高市", text)
        self.assertIn("【車種】\n4t", text)
        self.assertIn("【距離】\n約92km", text)
        self.assertIn("【運賃】\n8,000円", text)
        self.assertIn("【標準運賃目安】\n13,850円", text)
        self.assertIn("【標準比】\n123%（やや高い）", text)
        self.assertIn("【連絡先】", text)
        self.assertIn("会社名：テスト運送", text)
        self.assertIn("担当者：山田", text)
        self.assertIn("電話：090-1234-5678", text)
        self.assertIn("案件一覧から詳細をご確認ください。", text)
        self.assertNotIn("管理者確認待ち", text)

    def test_build_liff_job_created_text_shows_blank_category_as_missing(self) -> None:
        text = build_liff_job_created_text(
            {
                "pickup_location": "大阪府 大阪市",
                "delivery_location": "埼玉県 日高市",
                "job_category": "",
                "vehicle_type": "4t",
                "company_name": "テスト運送",
                "contact_name": "山田",
                "phone_number": "090-1234-5678",
            }
        )

        self.assertIn("【案件種別】\n未入力", text)

    def test_push_uses_line_push_api_without_returning_secret(self) -> None:
        settings = SimpleNamespace(line_channel_access_token="dummy-token")
        response = httpx.Response(200, json={})

        with patch("apps.api.app.services.line_push.httpx.post", return_value=response) as post:
            push_liff_job_created_message(
                settings,
                "Cgroup",
                {
                    "pickup_location": "大阪府 大阪市",
                    "delivery_location": "埼玉県 日高市",
                    "job_category": "spot",
                    "vehicle_type": "4t",
                    "company_name": "テスト運送",
                    "contact_name": "山田",
                    "phone_number": "09012345678",
                },
            )

        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.line.me/v2/bot/message/push")
        self.assertEqual(kwargs["json"]["to"], "Cgroup")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer dummy-token")
        self.assertNotIn("dummy-token", kwargs["json"]["messages"][0]["text"])

    def test_push_menu_sends_flex_to_user_with_session_url(self) -> None:
        settings = SimpleNamespace(
            line_channel_access_token="dummy-token",
            liff_base_url=None,
            liff_id="test-liff-id",
        )
        response = httpx.Response(200, json={})

        with patch("apps.api.app.services.line_push.httpx.post", return_value=response) as post:
            push_menu_message(settings, "Uuser", session_id="session-123")

        post.assert_called_once()
        _args, kwargs = post.call_args
        message = kwargs["json"]["messages"][0]
        first_button_uri = message["contents"]["footer"]["contents"][0]["action"]["uri"]
        self.assertEqual(kwargs["json"]["to"], "Uuser")
        self.assertEqual(message["type"], "flex")
        self.assertIn("session_id=session-123", first_button_uri)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer dummy-token")
        self.assertNotIn("dummy-token", str(kwargs["json"]))


if __name__ == "__main__":
    unittest.main()
