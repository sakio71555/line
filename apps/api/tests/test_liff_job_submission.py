from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from apps.api.app.schemas.liff_forms import LiffJobCreate
from apps.api.app.services.supabase import LIFF_JOB_INSERT_COLUMNS, create_liff_job


class LiffJobSubmissionTest(unittest.TestCase):
    def test_contact_fields_are_required(self) -> None:
        with self.assertRaises(ValidationError):
            LiffJobCreate(
                job_category="spot",
                pickup_prefecture="東京都",
                pickup_city="千代田区",
                delivery_prefecture="神奈川県",
                delivery_city="横浜市",
                vehicle_type="軽バン",
            )

    def test_minimum_payload_with_contact_is_accepted(self) -> None:
        form = LiffJobCreate(
            job_category="spot",
            pickup_prefecture="東京都",
            pickup_city="千代田区",
            delivery_prefecture="神奈川県",
            delivery_city="横浜市",
            vehicle_type="軽バン",
            company_name="テスト運送",
            contact_name="山田",
            phone_number="09012345678",
        )

        self.assertIsNone(form.scheduled_date)
        self.assertEqual(form.company_name, "テスト運送")
        self.assertEqual(form.contact_name, "山田")
        self.assertEqual(form.phone_number, "09012345678")
        self.assertIsNone(form.session_id)

    def test_minimum_payload_creates_open_job_with_contact(self) -> None:
        form = LiffJobCreate(
            job_category="spot",
            pickup_prefecture="東京都",
            pickup_city="千代田区",
            delivery_prefecture="神奈川県",
            delivery_city="横浜市",
            vehicle_type="軽バン",
            company_name="テスト運送",
            contact_name="山田",
            phone_number="09012345678",
        )

        with patch("apps.api.app.services.supabase.insert_row", side_effect=lambda _client, _table, payload: payload):
            payload = create_liff_job(object(), form)

        self.assertEqual(payload["source_type"], "liff_form")
        self.assertEqual(payload["job_category"], "spot")
        self.assertEqual(payload["status"], "open")
        self.assertEqual(payload["analysis_status"], "form_submitted")
        self.assertFalse(payload["review_required"])
        self.assertFalse(payload["contact_missing"])
        self.assertEqual(payload["contact_method"], "form")
        self.assertEqual(payload["company_name"], "テスト運送")
        self.assertEqual(payload["contact_name"], "山田")
        self.assertEqual(payload["phone_number"], "09012345678")
        self.assertEqual(payload["contact_phone"], "09012345678")
        self.assertEqual(payload["pickup_city"], "千代田区")
        self.assertEqual(payload["delivery_city"], "横浜市")
        self.assertIn("東京都 千代田区", payload["pickup_location"])
        self.assertIn("神奈川県 横浜市", payload["delivery_location"])
        self.assertEqual(payload["fare_calc_status"], "not_calculated")
        self.assertIsNone(payload["distance_km"])

    def test_liff_payload_uses_only_existing_job_columns(self) -> None:
        form = LiffJobCreate(
            job_category="spot",
            pickup_prefecture="東京都",
            pickup_city="千代田区",
            delivery_prefecture="神奈川県",
            delivery_city="横浜市",
            delivery_date="2026-05-02",
            delivery_time_text="午前中",
            vehicle_type="軽バン",
            distance_km=92.4,
            distance_text="約92km",
            distance_source="google_maps",
            standard_fare_yen=13850,
            fare_ratio_percent=122.7,
            fare_judgement="やや高い",
            fare_calc_status="ok",
            fare_calc_note="貨物軽自動車運送事業運賃料金表により計算",
            fare_vehicle_class="kei_cargo",
            fare_vehicle_label="貨物軽自動車",
            company_name="テスト運送",
            contact_name="山田",
            phone_number="09012345678",
        )

        with patch("apps.api.app.services.supabase.insert_row", side_effect=lambda _client, _table, payload: payload):
            payload = create_liff_job(object(), form)

        self.assertLessEqual(set(payload), LIFF_JOB_INSERT_COLUMNS)
        self.assertEqual(payload["source_type"], "liff_form")
        self.assertEqual(payload["delivery_date"], "2026-05-02")
        self.assertEqual(payload["delivery_time_text"], "午前中")
        self.assertEqual(payload["pickup_city"], "千代田区")
        self.assertEqual(payload["delivery_city"], "横浜市")
        self.assertEqual(payload["phone_number"], "09012345678")
        self.assertEqual(payload["distance_km"], 92.4)
        self.assertEqual(payload["standard_fare_yen"], 13850)
        self.assertEqual(payload["fare_ratio_percent"], 122.7)
        self.assertEqual(payload["fare_judgement"], "やや高い")
        self.assertEqual(payload["fare_calc_status"], "ok")
        self.assertEqual(payload["fare_vehicle_class"], "kei_cargo")
        for history_only_key in [
            "posted_at",
            "pickup_date",
            "pickup_time_text",
            "schedule_text",
            "date_confidence",
            "date_needs_review",
            "recurring",
            "import_batch_id",
            "history_message_hash",
            "source_display_name",
        ]:
            self.assertNotIn(history_only_key, payload)

    def test_schema_safety_migration_keeps_liff_and_history_source_types(self) -> None:
        sql = Path("supabase/migrations/009_liff_jobs_schema_safety.sql").read_text(encoding="utf-8")
        liff_open_sql = Path("supabase/migrations/010_liff_form_open_jobs.sql").read_text(encoding="utf-8")
        phone_sql = Path("supabase/migrations/011_jobs_phone_number.sql").read_text(encoding="utf-8")
        location_sql = Path("supabase/migrations/013_jobs_location_detail_fields.sql").read_text(encoding="utf-8")

        self.assertIn("line_group", sql)
        self.assertIn("liff_form", sql)
        self.assertIn("line_history_import", sql)
        self.assertIn("add column if not exists delivery_date date", sql)
        self.assertIn("notify pgrst, 'reload schema'", sql)
        self.assertIn("source_type = 'liff_form'", liff_open_sql)
        self.assertIn("status = 'open'", liff_open_sql)
        self.assertIn("review_required = false", liff_open_sql)
        self.assertIn("add column if not exists phone_number text", phone_sql)
        self.assertIn("add column if not exists pickup_city text", location_sql)
        self.assertIn("add column if not exists delivery_address text", location_sql)

    def test_session_context_sets_source_group_and_line_message(self) -> None:
        form = LiffJobCreate(
            job_category="spot",
            pickup_prefecture="東京都",
            pickup_city="千代田区",
            delivery_prefecture="神奈川県",
            delivery_city="横浜市",
            vehicle_type="軽バン",
            session_id="session-123",
            company_name="テスト運送",
            contact_name="山田",
            phone_number="09012345678",
        )
        liff_session = {
            "source_group_id": "Cgroup",
            "source_line_message_id": "line-message-uuid",
        }

        with patch("apps.api.app.services.supabase.insert_row", side_effect=lambda _client, _table, payload: payload):
            payload = create_liff_job(object(), form, liff_session=liff_session)

        self.assertEqual(payload["source_group_id"], "Cgroup")
        self.assertEqual(payload["source_line_message_id"], "line-message-uuid")
        self.assertEqual(payload["notify_group_id"], "Cgroup")

    def test_line_user_upsert_failure_does_not_block_job_creation(self) -> None:
        form = LiffJobCreate(
            job_category="spot",
            pickup_prefecture="東京都",
            pickup_city="千代田区",
            delivery_prefecture="神奈川県",
            delivery_city="横浜市",
            vehicle_type="軽バン",
            company_name="テスト運送",
            contact_name="山田",
            phone_number="09012345678",
            line_user_id="Uuser",
        )

        with (
            patch("apps.api.app.services.supabase.upsert_line_user", side_effect=RuntimeError("upsert failed")),
            patch("apps.api.app.services.supabase.insert_row", side_effect=lambda _client, _table, payload: payload),
        ):
            payload = create_liff_job(object(), form)

        self.assertEqual(payload["source_type"], "liff_form")
        self.assertEqual(payload["phone_number"], "09012345678")


if __name__ == "__main__":
    unittest.main()
