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


class AdminStatusUpdatesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.supabase = SupabaseRestClient("https://example.supabase.co", "test-secret-key")

    def test_status_updates_endpoint_returns_200_with_rows(self) -> None:
        response = self.get_status_updates_with_rows([status_update_row(candidates=[candidate_row()])])

        self.assertEqual(response.status_code, 200)
        updates = response.json()["status_updates"]
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["candidates"][0]["id"], "job-candidate-id")

    def test_status_updates_endpoint_returns_200_with_empty_rows(self) -> None:
        response = self.get_status_updates_with_rows([])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status_updates": []})

    def test_status_updates_endpoint_accepts_candidates_null(self) -> None:
        response = self.get_status_updates_with_rows([status_update_row(candidates=None)])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status_updates"][0]["candidates"], [])

    def test_status_updates_endpoint_accepts_candidates_empty_array(self) -> None:
        response = self.get_status_updates_with_rows([status_update_row(candidates=[])])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status_updates"][0]["candidates"], [])

    def test_status_updates_endpoint_accepts_candidates_json_string(self) -> None:
        response = self.get_status_updates_with_rows([status_update_row(candidates='[{"id":"job-json-id","status":"open"}]')])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status_updates"][0]["candidates"][0]["id"], "job-json-id")

    def test_status_updates_endpoint_accepts_candidates_object(self) -> None:
        response = self.get_status_updates_with_rows([status_update_row(candidates={"id": "job-object-id", "status": "open"})])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status_updates"][0]["candidates"][0]["id"], "job-object-id")

    def test_status_updates_endpoint_accepts_null_possible_and_review_dates(self) -> None:
        response = self.get_status_updates_with_rows(
            [
                status_update_row(
                    possible_job_id=None,
                    applied_at=None,
                    ignored_at=None,
                    reviewed_at=None,
                )
            ]
        )

        self.assertEqual(response.status_code, 200)
        update = response.json()["status_updates"][0]
        self.assertIsNone(update["possible_job_id"])
        self.assertIsNone(update["applied_at"])
        self.assertIsNone(update["ignored_at"])
        self.assertIsNone(update["reviewed_at"])

    def test_status_updates_endpoint_falls_back_when_optional_columns_are_missing(self) -> None:
        request = httpx.Request("GET", "https://example.supabase.co/rest/v1/job_status_updates")
        missing_column = httpx.Response(
            400,
            json={
                "code": "42703",
                "message": "column job_status_updates.reported_by_display_name does not exist",
            },
            request=request,
        )
        fallback = httpx.Response(200, json=[status_update_row(include_reporter_fields=False)], request=request)

        with (
            patch("apps.api.app.routers.admin_status_updates.get_supabase_client", return_value=self.supabase),
            patch("apps.api.app.services.supabase.httpx.get", side_effect=[missing_column, fallback]),
        ):
            response = self.client.get("/admin/status-updates?scope=all")

        self.assertEqual(response.status_code, 200)
        update = response.json()["status_updates"][0]
        self.assertIsNone(update["reported_by_line_user_id"])
        self.assertFalse(update["is_reported_by_job_owner"])

    def test_status_updates_scope_mine_uses_verified_owner(self) -> None:
        with (
            patch("apps.api.app.routers.admin_status_updates.verify_line_id_token", return_value={"line_user_id": "Uowner"}),
            patch("apps.api.app.routers.admin_status_updates.get_supabase_client", return_value=self.supabase),
            patch("apps.api.app.routers.admin_status_updates.fetch_admin_status_updates", return_value=[]) as fetch_updates,
        ):
            response = self.client.get(
                "/admin/status-updates?scope=mine",
                headers={"Authorization": "Bearer test-id-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status_updates": []})
        self.assertEqual(fetch_updates.call_args.kwargs["owner_line_user_id"], "Uowner")

    def test_apply_scope_mine_allows_owner_job(self) -> None:
        result = {
            "job": {"id": "job-id", "status": "assigned"},
            "status_update": status_update_row(possible_job_id="job-id"),
        }
        with (
            patch("apps.api.app.routers.admin_status_updates.verify_line_id_token", return_value={"line_user_id": "Uowner", "display_name": "Owner"}),
            patch("apps.api.app.routers.admin_status_updates.fetch_status_update_by_id", return_value=status_update_row(possible_job_id="job-id")),
            patch("apps.api.app.routers.admin_status_updates.fetch_admin_job_by_id", return_value={"id": "job-id", "created_by_line_user_id": "Uowner"}),
            patch("apps.api.app.routers.admin_status_updates.apply_status_update", return_value=result) as apply_update,
        ):
            response = self.client.post(
                "/admin/status-updates/status-update-id/apply?scope=mine",
                headers={"Authorization": "Bearer test-id-token"},
                json={"job_id": "job-id", "new_status": "assigned"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"]["status"], "assigned")
        apply_update.assert_called_once()

    def test_apply_scope_mine_forbids_other_owner_job(self) -> None:
        with (
            patch("apps.api.app.routers.admin_status_updates.verify_line_id_token", return_value={"line_user_id": "Uowner", "display_name": "Owner"}),
            patch("apps.api.app.routers.admin_status_updates.fetch_status_update_by_id", return_value=status_update_row(possible_job_id="job-id")),
            patch("apps.api.app.routers.admin_status_updates.fetch_admin_job_by_id", return_value={"id": "job-id", "created_by_line_user_id": "Uother"}),
            patch("apps.api.app.routers.admin_status_updates.apply_status_update") as apply_update,
        ):
            response = self.client.post(
                "/admin/status-updates/status-update-id/apply?scope=mine",
                headers={"Authorization": "Bearer test-id-token"},
                json={"job_id": "job-id", "new_status": "assigned"},
            )

        self.assertEqual(response.status_code, 403)
        apply_update.assert_not_called()

    def test_ignore_falls_back_when_optional_columns_are_missing(self) -> None:
        request = httpx.Request("PATCH", "https://example.supabase.co/rest/v1/job_status_updates")
        missing_column = httpx.Response(
            400,
            json={
                "code": "42703",
                "message": "column job_status_updates.reported_by_display_name does not exist",
            },
            request=request,
        )
        fallback_row = status_update_row(include_reporter_fields=False, ignored_at="2026-05-02T00:00:00+00:00")
        fallback = httpx.Response(200, json=[fallback_row], request=request)

        with (
            patch("apps.api.app.routers.admin_status_updates.get_supabase_client", return_value=self.supabase),
            patch("apps.api.app.services.supabase.httpx.patch", side_effect=[missing_column, fallback]),
        ):
            response = self.client.post(
                "/admin/status-updates/status-update-id/ignore?scope=all",
                json={"reviewed_by": "admin"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status_update"]["id"], "status-update-id")

    def test_status_updates_default_scope_requires_line_login(self) -> None:
        with patch("apps.api.app.routers.admin_status_updates.fetch_admin_status_updates") as fetch_updates:
            response = self.client.get("/admin/status-updates")

        self.assertEqual(response.status_code, 401)
        fetch_updates.assert_not_called()

    def get_status_updates_with_rows(self, rows: list[dict]) -> httpx.Response:
        request = httpx.Request("GET", "https://example.supabase.co/rest/v1/job_status_updates")
        with (
            patch("apps.api.app.routers.admin_status_updates.get_supabase_client", return_value=self.supabase),
            patch(
                "apps.api.app.services.supabase.httpx.get",
                return_value=httpx.Response(200, json=rows, request=request),
            ),
        ):
            return self.client.get("/admin/status-updates?scope=all")


def status_update_row(
    *,
    candidates=(),
    possible_job_id: str | None = "job-id",
    applied_at: str | None = None,
    ignored_at: str | None = None,
    reviewed_at: str | None = None,
    include_reporter_fields: bool = True,
) -> dict:
    row = {
        "id": "status-update-id",
        "source_line_message_id": "line-message-id",
        "source_group_id": "Cgroup",
        "source_user_id": "Uuser",
        "source_message_id": "source-message-id",
        "raw_text": "メンバーさんに対応頂きました。",
        "update_type": "job_closed",
        "proposed_status": "assigned",
        "possible_job_id": possible_job_id,
        "candidates": [] if candidates == () else candidates,
        "confidence": 0.92,
        "review_required": True,
        "reason": "終了報告候補",
        "created_at": "2026-05-02T00:00:00+00:00",
        "reviewed_at": reviewed_at,
        "reviewed_by": None,
        "applied_at": applied_at,
        "ignored_at": ignored_at,
    }
    if include_reporter_fields:
        row.update(
            {
                "reported_by_line_user_id": "Uuser",
                "reported_by_display_name": "投稿者",
                "is_reported_by_job_owner": True,
            }
        )
    return row


def candidate_row() -> dict:
    return {
        "id": "job-candidate-id",
        "pickup_location": "大阪府枚方市",
        "delivery_location": "埼玉県日高市",
        "status": "open",
        "created_at": "2026-05-02T00:00:00+00:00",
    }


if __name__ == "__main__":
    unittest.main()
