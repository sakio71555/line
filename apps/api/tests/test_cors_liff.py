from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-line-channel-secret")

from apps.api.app.main import app  # noqa: E402
from apps.api.app.routers.liff_forms import resolve_liff_job_notify_group_id  # noqa: E402
from apps.api.app.core.config import get_settings  # noqa: E402
from apps.api.app.services.line_push import LinePushError  # noqa: E402
from apps.api.app.services.supabase import SupabaseRequestError  # noqa: E402


class LiffCorsTest(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
            line_channel_access_token=None,
            line_default_notify_group_id=None,
        )
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_trycloudflare_preflight_for_liff_jobs(self) -> None:
        origin = "https://song-threats-knock-html.trycloudflare.com"
        response = self.client.options(
            "/liff/jobs",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        self.assertIn(response.status_code, {200, 204})
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        self.assertIn("POST", response.headers.get("access-control-allow-methods", ""))

    def test_liff_jobs_post_creates_open_job(self) -> None:
        expected_job = {
            "source_type": "liff_form",
            "status": "open",
            "analysis_status": "form_submitted",
            "review_required": False,
        }
        payload = {
            "job_category": "spot",
            "pickup_prefecture": "東京都",
            "pickup_city": "千代田区",
            "pickup_address": None,
            "delivery_prefecture": "神奈川県",
            "delivery_city": "横浜市",
            "delivery_address": None,
            "scheduled_date": None,
            "scheduled_time_text": None,
            "delivery_date": None,
            "delivery_time_text": None,
            "vehicle_type": "軽バン",
            "vehicle_count": 1,
            "cargo_type": None,
            "price": None,
            "tax_type": "不明",
            "highway_fee_note": None,
            "fee_note": None,
            "notes": None,
            "company_name": "テスト運送",
            "contact_name": "山田",
            "phone_number": "09012345678",
            "line_user_id": None,
            "display_name": None,
            "session_id": None,
        }

        with (
            patch("apps.api.app.routers.liff_forms.get_supabase_client", return_value=object()),
            patch("apps.api.app.routers.liff_forms.create_liff_job", return_value=expected_job),
        ):
            response = self.client.post("/liff/jobs", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"], expected_job)

    def test_liff_jobs_post_without_session_id_is_accepted(self) -> None:
        expected_job = {
            "source_type": "liff_form",
            "status": "open",
            "analysis_status": "form_submitted",
            "review_required": False,
            "contact_missing": False,
        }
        payload = {
            "job_category": "spot",
            "pickup_prefecture": "東京都",
            "pickup_city": "千代田区",
            "delivery_prefecture": "神奈川県",
            "delivery_city": "横浜市",
            "vehicle_type": "軽バン",
            "company_name": "テスト運送",
            "contact_name": "山田",
            "phone_number": "09012345678",
        }

        with (
            patch("apps.api.app.routers.liff_forms.get_supabase_client", return_value=object()),
            patch("apps.api.app.routers.liff_forms.fetch_liff_session_by_session_id") as fetch_session,
            patch("apps.api.app.routers.liff_forms.create_liff_job", return_value=expected_job) as create_job,
            patch("apps.api.app.routers.liff_forms.push_liff_job_created_message") as push_message,
            patch("apps.api.app.routers.liff_forms.update_job_notification_result") as update_notification,
        ):
            response = self.client.post("/liff/jobs", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"], expected_job)
        fetch_session.assert_not_called()
        create_job.assert_called_once()
        self.assertIsNone(create_job.call_args.kwargs["liff_session"])
        push_message.assert_not_called()
        update_notification.assert_called_once()

    def test_liff_jobs_supabase_error_returns_safe_detail(self) -> None:
        payload = {
            "job_category": "spot",
            "pickup_prefecture": "東京都",
            "pickup_city": "千代田区",
            "delivery_prefecture": "神奈川県",
            "delivery_city": "横浜市",
            "vehicle_type": "軽バン",
            "company_name": "テスト運送",
            "contact_name": "山田",
            "phone_number": "09012345678",
        }
        supabase_error = SupabaseRequestError(
            operation="insert",
            table="jobs",
            status_code=400,
            message="Could not find the 'delivery_date' column of 'jobs' in the schema cache",
            payload_keys=["delivery_date", "source_type"],
        )

        with (
            patch("apps.api.app.routers.liff_forms.get_supabase_client", return_value=object()),
            patch("apps.api.app.routers.liff_forms.create_liff_job", side_effect=supabase_error),
        ):
            response = self.client.post("/liff/jobs", json=payload)

        self.assertEqual(response.status_code, 502)
        detail = response.json()["detail"]
        self.assertEqual(detail["message"], "保存に失敗しました")
        self.assertEqual(detail["reason"], "DBカラム不一致の可能性があります")
        self.assertEqual(detail["fields"], ["delivery_date"])
        self.assertEqual(detail["payload_keys"], ["delivery_date", "source_type"])

    def test_liff_jobs_post_uses_session_and_pushes_group_notification(self) -> None:
        expected_job = {
            "id": "job-id",
            "source_type": "liff_form",
            "source_group_id": "Cgroup",
            "pickup_location": "東京都 千代田区",
            "delivery_location": "神奈川県 横浜市",
            "vehicle_type": "軽バン",
            "status": "open",
            "analysis_status": "form_submitted",
            "review_required": False,
            "contact_missing": False,
        }
        payload = {
            "job_category": "spot",
            "pickup_prefecture": "東京都",
            "pickup_city": "千代田区",
            "delivery_prefecture": "神奈川県",
            "delivery_city": "横浜市",
            "vehicle_type": "軽バン",
            "session_id": "session-123",
            "company_name": "テスト運送",
            "contact_name": "山田",
            "phone_number": "09012345678",
        }
        liff_session = {
            "session_id": "session-123",
            "source_group_id": "Cgroup",
            "source_line_message_id": "line-message-id",
        }

        with (
            patch("apps.api.app.routers.liff_forms.get_supabase_client", return_value=object()),
            patch("apps.api.app.routers.liff_forms.fetch_liff_session_by_session_id", return_value=liff_session) as fetch_session,
            patch("apps.api.app.routers.liff_forms.create_liff_job", return_value=expected_job) as create_job,
            patch("apps.api.app.routers.liff_forms.mark_liff_session_used") as mark_used,
            patch("apps.api.app.routers.liff_forms.push_liff_job_created_message") as push_message,
            patch("apps.api.app.routers.liff_forms.update_job_notification_result") as update_notification,
        ):
            response = self.client.post("/liff/jobs", json=payload)

        self.assertEqual(response.status_code, 200)
        fetch_session.assert_called_once()
        create_job.assert_called_once()
        self.assertEqual(create_job.call_args.kwargs["liff_session"], liff_session)
        mark_used.assert_called_once()
        push_message.assert_called_once()
        self.assertEqual(push_message.call_args.args[1], "Cgroup")
        update_notification.assert_called()

    def test_liff_jobs_post_without_group_skips_notification_but_succeeds(self) -> None:
        expected_job = {
            "id": "job-id",
            "source_type": "liff_form",
            "pickup_location": "東京都 千代田区",
            "delivery_location": "神奈川県 横浜市",
            "vehicle_type": "軽バン",
            "status": "open",
            "analysis_status": "form_submitted",
            "review_required": False,
            "contact_missing": False,
        }
        payload = {
            "job_category": "spot",
            "pickup_prefecture": "東京都",
            "pickup_city": "千代田区",
            "delivery_prefecture": "神奈川県",
            "delivery_city": "横浜市",
            "vehicle_type": "軽バン",
            "company_name": "テスト運送",
            "contact_name": "山田",
            "phone_number": "09012345678",
        }

        with (
            patch("apps.api.app.routers.liff_forms.get_supabase_client", return_value=object()),
            patch("apps.api.app.routers.liff_forms.create_liff_job", return_value=expected_job),
            patch("apps.api.app.routers.liff_forms.push_liff_job_created_message") as push_message,
            patch("apps.api.app.routers.liff_forms.update_job_notification_result") as update_notification,
        ):
            response = self.client.post("/liff/jobs", json=payload)

        self.assertEqual(response.status_code, 200)
        push_message.assert_not_called()
        update_notification.assert_called_once()

    def test_liff_jobs_post_uses_default_notify_group_without_session(self) -> None:
        app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
            line_channel_access_token=None,
            line_default_notify_group_id="Cdefault",
        )
        expected_job = {
            "id": "job-id",
            "source_type": "liff_form",
            "pickup_location": "東京都 千代田区",
            "delivery_location": "神奈川県 横浜市",
            "vehicle_type": "軽バン",
            "status": "open",
            "analysis_status": "form_submitted",
            "review_required": False,
            "contact_missing": False,
        }
        payload = {
            "job_category": "spot",
            "pickup_prefecture": "東京都",
            "pickup_city": "千代田区",
            "delivery_prefecture": "神奈川県",
            "delivery_city": "横浜市",
            "vehicle_type": "軽バン",
            "company_name": "テスト運送",
            "contact_name": "山田",
            "phone_number": "09012345678",
        }

        with (
            patch("apps.api.app.routers.liff_forms.get_supabase_client", return_value=object()),
            patch("apps.api.app.routers.liff_forms.create_liff_job", return_value=expected_job),
            patch("apps.api.app.routers.liff_forms.push_liff_job_created_message") as push_message,
            patch("apps.api.app.routers.liff_forms.update_job_notification_result") as update_notification,
        ):
            response = self.client.post("/liff/jobs", json=payload)

        self.assertEqual(response.status_code, 200)
        push_message.assert_called_once()
        self.assertEqual(push_message.call_args.args[1], "Cdefault")
        update_notification.assert_called()

    def test_liff_jobs_post_succeeds_when_line_push_fails(self) -> None:
        expected_job = {
            "id": "job-id",
            "source_type": "liff_form",
            "source_group_id": "Cgroup",
            "pickup_location": "東京都 千代田区",
            "delivery_location": "神奈川県 横浜市",
            "vehicle_type": "軽バン",
            "status": "open",
            "analysis_status": "form_submitted",
            "review_required": False,
            "contact_missing": False,
        }
        payload = {
            "job_category": "spot",
            "pickup_prefecture": "東京都",
            "pickup_city": "千代田区",
            "delivery_prefecture": "神奈川県",
            "delivery_city": "横浜市",
            "vehicle_type": "軽バン",
            "session_id": "session-123",
            "company_name": "テスト運送",
            "contact_name": "山田",
            "phone_number": "09012345678",
        }
        liff_session = {
            "session_id": "session-123",
            "source_group_id": "Cgroup",
            "source_line_message_id": "line-message-id",
        }

        with (
            patch("apps.api.app.routers.liff_forms.get_supabase_client", return_value=object()),
            patch("apps.api.app.routers.liff_forms.fetch_liff_session_by_session_id", return_value=liff_session),
            patch("apps.api.app.routers.liff_forms.create_liff_job", return_value=expected_job),
            patch("apps.api.app.routers.liff_forms.mark_liff_session_used"),
            patch(
                "apps.api.app.routers.liff_forms.push_liff_job_created_message",
                side_effect=LinePushError("LINE push request failed with status 403"),
            ),
            patch("apps.api.app.routers.liff_forms.update_job_notification_result") as update_notification,
        ):
            response = self.client.post("/liff/jobs", json=payload)

        self.assertEqual(response.status_code, 200)
        notify_kwargs = update_notification.call_args.kwargs
        self.assertEqual(notify_kwargs["notify_group_id"], "Cgroup")
        self.assertEqual(notify_kwargs["notify_error"], "LinePushError")

    def test_notify_group_priority_uses_session_then_job_then_default(self) -> None:
        settings = SimpleNamespace(line_default_notify_group_id="Cdefault")

        self.assertEqual(
            resolve_liff_job_notify_group_id(settings, {"notify_group_id": "Cjob"}, {"source_group_id": "Csession"}),
            "Csession",
        )
        self.assertEqual(
            resolve_liff_job_notify_group_id(settings, {"notify_group_id": "Cjob"}, None),
            "Cjob",
        )
        self.assertEqual(
            resolve_liff_job_notify_group_id(settings, {}, None),
            "Cdefault",
        )

    def test_validation_error_response_exposes_only_fields(self) -> None:
        response = self.client.post("/liff/jobs", json={"job_category": "spot"})

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["detail"]["message"], "入力データの形式が正しくありません")
        self.assertIn("pickup_prefecture", body["detail"]["fields"])
        self.assertIn("pickup_city", body["detail"]["fields"])
        self.assertIn("delivery_prefecture", body["detail"]["fields"])
        self.assertIn("delivery_city", body["detail"]["fields"])
        self.assertIn("vehicle_type", body["detail"]["fields"])
        self.assertIn("company_name", body["detail"]["fields"])
        self.assertIn("contact_name", body["detail"]["fields"])
        self.assertIn("phone_number", body["detail"]["fields"])


if __name__ == "__main__":
    unittest.main()
