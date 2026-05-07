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
from apps.api.app.services.supabase import SupabaseRestClient  # noqa: E402


class AdminJobsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.supabase = SupabaseRestClient("https://example.supabase.co", "test-secret-key")

    def test_admin_jobs_includes_liff_form_open_job(self) -> None:
        request = httpx.Request("GET", "https://example.supabase.co/rest/v1/jobs")
        rows = [
            job_row(
                job_id="new-liff-job",
                source_type="liff_form",
                status="open",
                analysis_status="form_submitted",
                review_required=False,
                created_at="2026-05-02T12:00:00+00:00",
            )
        ]

        with (
            patch("apps.api.app.routers.admin_jobs.get_supabase_client", return_value=self.supabase),
            patch(
                "apps.api.app.services.supabase.httpx.get",
                return_value=httpx.Response(200, json=rows, request=request),
            ) as get,
        ):
            response = self.client.get("/admin/jobs?scope=all")

        self.assertEqual(response.status_code, 200)
        jobs = response.json()["jobs"]
        self.assertEqual(jobs[0]["id"], "new-liff-job")
        self.assertEqual(jobs[0]["source_type"], "liff_form")
        self.assertEqual(jobs[0]["status"], "open")
        self.assertEqual(jobs[0]["analysis_status"], "form_submitted")
        self.assertFalse(jobs[0]["review_required"])

        params = get.call_args.kwargs["params"]
        self.assertIn("open", params["status"])
        self.assertIn("needs_review", params["status"])
        self.assertIn("created_at.desc", params["order"])
        self.assertGreaterEqual(int(params["limit"]), 100)

    def test_admin_jobs_keeps_created_at_desc_request_for_latest_first(self) -> None:
        request = httpx.Request("GET", "https://example.supabase.co/rest/v1/jobs")
        rows = [
            job_row(job_id="latest", created_at="2026-05-02T12:00:00+00:00"),
            job_row(job_id="older", created_at="2026-05-01T12:00:00+00:00"),
        ]

        with (
            patch("apps.api.app.routers.admin_jobs.get_supabase_client", return_value=self.supabase),
            patch(
                "apps.api.app.services.supabase.httpx.get",
                return_value=httpx.Response(200, json=rows, request=request),
            ) as get,
        ):
            response = self.client.get("/admin/jobs?scope=all")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([job["id"] for job in response.json()["jobs"]], ["latest", "older"])
        self.assertEqual(get.call_args.kwargs["params"]["order"], "created_at.desc")
        self.assertNotIn("created_by_line_user_id", get.call_args.kwargs["params"])

    def test_admin_jobs_scope_mine_filters_by_verified_line_user(self) -> None:
        request = httpx.Request("GET", "https://example.supabase.co/rest/v1/jobs")
        rows = [
            job_row(
                job_id="my-job",
                source_type="liff_form",
                status="open",
                review_required=False,
                created_at="2026-05-02T12:00:00+00:00",
                created_by_line_user_id="Uowner",
            )
        ]

        with (
            patch("apps.api.app.routers.admin_jobs.get_supabase_client", return_value=self.supabase),
            patch(
                "apps.api.app.routers.admin_jobs.verify_line_id_token",
                return_value={"line_user_id": "Uowner", "display_name": "Owner"},
            ) as verify,
            patch(
                "apps.api.app.services.supabase.httpx.get",
                return_value=httpx.Response(200, json=rows, request=request),
            ) as get,
        ):
            response = self.client.get(
                "/admin/jobs?scope=mine",
                headers={"Authorization": "Bearer test-id-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["jobs"][0]["id"], "my-job")
        verify.assert_called_once()
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["created_by_line_user_id"], "eq.Uowner")

    def test_admin_jobs_scope_mine_requires_line_login(self) -> None:
        with patch("apps.api.app.routers.admin_jobs.fetch_admin_jobs") as fetch_jobs:
            response = self.client.get("/admin/jobs?scope=mine")

        self.assertEqual(response.status_code, 401)
        fetch_jobs.assert_not_called()

    def test_admin_jobs_default_scope_requires_line_login(self) -> None:
        with patch("apps.api.app.routers.admin_jobs.fetch_admin_jobs") as fetch_jobs:
            response = self.client.get("/admin/jobs")

        self.assertEqual(response.status_code, 401)
        fetch_jobs.assert_not_called()

    def test_mine_update_allows_owner_job(self) -> None:
        updated = job_row(
            job_id="my-job",
            status="assigned",
            review_required=False,
            created_by_line_user_id="Uowner",
        )

        with (
            patch(
                "apps.api.app.routers.admin_jobs.verify_line_id_token",
                return_value={"line_user_id": "Uowner", "display_name": "Owner"},
            ),
            patch(
                "apps.api.app.routers.admin_jobs.fetch_admin_job_by_id",
                return_value=job_row(job_id="my-job", created_by_line_user_id="Uowner"),
            ),
            patch("apps.api.app.routers.admin_jobs.update_admin_job", return_value=updated) as update_job,
        ):
            response = self.client.patch(
                "/admin/jobs/my-job?scope=mine",
                headers={"Authorization": "Bearer test-id-token"},
                json={"status": "assigned"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"]["status"], "assigned")
        update_job.assert_called_once()

    def test_mine_update_forbids_other_owner_job(self) -> None:
        with (
            patch(
                "apps.api.app.routers.admin_jobs.verify_line_id_token",
                return_value={"line_user_id": "Uowner", "display_name": "Owner"},
            ),
            patch(
                "apps.api.app.routers.admin_jobs.fetch_admin_job_by_id",
                return_value=job_row(job_id="other-job", created_by_line_user_id="Uother"),
            ),
            patch("apps.api.app.routers.admin_jobs.update_admin_job") as update_job,
        ):
            response = self.client.patch(
                "/admin/jobs/other-job?scope=mine",
                headers={"Authorization": "Bearer test-id-token"},
                json={"status": "assigned"},
            )

        self.assertEqual(response.status_code, 403)
        update_job.assert_not_called()

    def test_all_scope_update_keeps_existing_admin_behavior_without_token(self) -> None:
        updated = job_row(job_id="admin-job", status="completed", review_required=False)

        with patch("apps.api.app.routers.admin_jobs.update_admin_job", return_value=updated) as update_job:
            response = self.client.patch(
                "/admin/jobs/admin-job?scope=all",
                json={"status": "completed"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"]["status"], "completed")
        update_job.assert_called_once()


def job_row(
    *,
    job_id: str,
    source_type: str = "liff_form",
    status: str = "needs_review",
    analysis_status: str = "form_submitted",
    review_required: bool = True,
    created_at: str = "2026-05-02T12:00:00+00:00",
    created_by_line_user_id: str | None = None,
) -> dict:
    return {
        "id": job_id,
        "source_type": source_type,
        "source_line_message_id": None,
        "source_group_id": None,
        "source_user_id": None,
        "source_message_id": None,
        "raw_text": "案件種別: spot",
        "job_category": "spot",
        "pickup_location": "東京都 千代田区",
        "delivery_location": "神奈川県 横浜市",
        "pickup_prefecture": "東京都",
        "delivery_prefecture": "神奈川県",
        "scheduled_date": None,
        "scheduled_time_text": None,
        "delivery_date": None,
        "posted_at": None,
        "pickup_date": None,
        "pickup_time_text": None,
        "delivery_time_text": None,
        "schedule_text": None,
        "date_confidence": None,
        "date_needs_review": False,
        "recurring": False,
        "import_batch_id": None,
        "history_message_hash": None,
        "vehicle_type": "軽バン",
        "vehicle_count": 1,
        "cargo_type": None,
        "price": None,
        "tax_type": "不明",
        "fee_note": None,
        "highway_fee_note": None,
        "budget_note": None,
        "company_name": None,
        "contact_name": None,
        "phone_number": None,
        "contact_line_user_id": None,
        "contact_display_name": None,
        "contact_phone": None,
        "contact_method": "form",
        "contact_missing": True,
        "phone_numbers": [],
        "notes": None,
        "status": status,
        "analysis_status": analysis_status,
        "confidence": None,
        "missing_fields": [],
        "review_required": review_required,
        "created_by_line_user_id": created_by_line_user_id,
        "created_by_display_name": None,
        "assigned_at": None,
        "in_progress_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "status_updated_at": None,
        "status_updated_by": None,
        "closed_reason": None,
        "closed_reported_by_line_user_id": None,
        "closed_reported_at": None,
        "notify_group_id": None,
        "notified_at": None,
        "notify_error": None,
        "created_at": created_at,
        "updated_at": created_at,
    }


if __name__ == "__main__":
    unittest.main()
