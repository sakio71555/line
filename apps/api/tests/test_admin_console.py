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
from apps.api.app.routers import admin_console  # noqa: E402


class AdminConsoleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        app.dependency_overrides[admin_console.get_settings] = lambda: SimpleNamespace(
            admin_console_token="correct-admin-token",
            admin_console_password=None,
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_admin_console_jobs_requires_authentication(self) -> None:
        with patch("apps.api.app.routers.admin_console.fetch_admin_console_jobs") as fetch_jobs:
            response = self.client.get("/admin-console/jobs")

        self.assertEqual(response.status_code, 401)
        fetch_jobs.assert_not_called()

    def test_admin_console_jobs_rejects_wrong_authentication(self) -> None:
        with patch("apps.api.app.routers.admin_console.fetch_admin_console_jobs") as fetch_jobs:
            response = self.client.get(
                "/admin-console/jobs",
                headers={"X-Admin-Token": "wrong-admin-token"},
            )

        self.assertEqual(response.status_code, 403)
        fetch_jobs.assert_not_called()

    def test_admin_console_jobs_returns_all_jobs_with_correct_authentication(self) -> None:
        rows = [
            job_row("owner-job", "Uowner", "open"),
            job_row("other-job", "Uother", "closed"),
            job_row("deleted-job", None, "deleted", deleted_at="2026-05-10T00:00:00+00:00"),
        ]
        with patch(
            "apps.api.app.routers.admin_console.fetch_admin_console_jobs",
            return_value=rows,
        ):
            response = self.client.get(
                "/admin-console/jobs",
                headers={"X-Admin-Token": "correct-admin-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([job["id"] for job in response.json()["jobs"]], ["owner-job", "other-job", "deleted-job"])

    def test_admin_console_filters_deleted_only(self) -> None:
        rows = [
            job_row("open-job", "Uowner", "open"),
            job_row("deleted-job", "Uowner", "deleted", deleted_at="2026-05-10T00:00:00+00:00"),
        ]
        with patch("apps.api.app.routers.admin_console.fetch_admin_console_jobs", return_value=rows):
            response = self.client.get(
                "/admin-console/jobs?deleted_only=true",
                headers={"X-Admin-Token": "correct-admin-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([job["id"] for job in response.json()["jobs"]], ["deleted-job"])

    def test_admin_console_can_change_any_job_status(self) -> None:
        updated = job_row("other-job", "Uother", "assigned")
        with patch(
            "apps.api.app.routers.admin_console.set_admin_job_status",
            return_value=updated,
        ) as set_status:
            response = self.client.post(
                "/admin-console/jobs/other-job/status",
                headers={"X-Admin-Token": "correct-admin-token"},
                json={"new_status": "assigned", "reason": "管理者確認"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"]["status"], "assigned")
        self.assertEqual(set_status.call_args.kwargs["changed_by_name"], "admin_console")
        self.assertEqual(set_status.call_args.kwargs["source_type"], "admin_console")

    def test_admin_console_can_logically_delete_any_job(self) -> None:
        deleted = job_row("other-job", "Uother", "deleted", deleted_at="2026-05-10T00:00:00+00:00")
        with patch(
            "apps.api.app.routers.admin_console.delete_admin_job",
            return_value=deleted,
        ) as delete_job:
            response = self.client.post(
                "/admin-console/jobs/other-job/delete",
                headers={"X-Admin-Token": "correct-admin-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"]["status"], "deleted")
        self.assertEqual(delete_job.call_args.kwargs["delete_reason"], "管理者削除")
        self.assertEqual(delete_job.call_args.kwargs["changed_by_name"], "admin_console")
        self.assertEqual(delete_job.call_args.kwargs["source_type"], "admin_console")

    def test_admin_console_can_restore_deleted_job(self) -> None:
        restored = job_row("deleted-job", "Uowner", "open")
        with patch(
            "apps.api.app.routers.admin_console.restore_admin_console_job",
            return_value=restored,
        ) as restore_job:
            response = self.client.post(
                "/admin-console/jobs/deleted-job/restore",
                headers={"X-Admin-Token": "correct-admin-token"},
                json={"status": "open", "reason": "復元確認"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"]["status"], "open")
        self.assertEqual(restore_job.call_args.kwargs["restore_status"], "open")


def job_row(
    job_id: str,
    owner: str | None,
    status: str,
    *,
    deleted_at: str | None = None,
) -> dict[str, object]:
    return {
        "id": job_id,
        "source_type": "liff_form",
        "posting_type": "delivery",
        "job_category": "spot",
        "title": None,
        "free_text": None,
        "pickup_location": "高知県高知市",
        "delivery_location": "愛媛県松山市",
        "pickup_prefecture": "高知県",
        "pickup_city": "高知市",
        "pickup_address": "",
        "delivery_prefecture": "愛媛県",
        "delivery_city": "松山市",
        "delivery_address": "",
        "vehicle_type": "軽バン",
        "price": 17000,
        "fare_ratio_text": "79%",
        "fare_judgement": "やや安い",
        "company_name": "テスト運送",
        "contact_name": "山田",
        "phone_number": "09000000000",
        "created_by_line_user_id": owner,
        "status": status,
        "deleted_at": deleted_at,
        "created_at": "2026-05-10T00:00:00+00:00",
        "updated_at": "2026-05-10T01:00:00+00:00",
    }


if __name__ == "__main__":
    unittest.main()
