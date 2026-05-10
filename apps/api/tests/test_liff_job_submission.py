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

    def test_other_posting_does_not_require_pickup_or_delivery(self) -> None:
        form = LiffJobCreate(
            posting_type="other",
            job_category="driver_recruitment",
            title="冷蔵軽貨物ドライバー募集",
            free_text="都内中心に一都三県で稼働できる方を募集しています。",
            target_area="一都三県",
            company_name="テスト運送",
            contact_name="山田",
            phone_number="09012345678",
        )

        self.assertEqual(form.posting_type, "other")
        self.assertIsNone(form.pickup_prefecture)
        self.assertEqual(form.title, "冷蔵軽貨物ドライバー募集")

    def test_delivery_posting_requires_pickup_and_delivery(self) -> None:
        with self.assertRaises(ValidationError):
            LiffJobCreate(
                posting_type="delivery",
                job_category="spot",
                title="配送案件",
                company_name="テスト運送",
                contact_name="山田",
                phone_number="09012345678",
            )

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

    def test_other_posting_creates_open_job_without_distance(self) -> None:
        form = LiffJobCreate(
            posting_type="other",
            job_category="referral_request",
            title="定期案件の紹介依頼",
            free_text="老舗のお弁当を配送できるドライバーさんを探しています。\n稼働条件は相談可能です。",
            target_area="都内中心",
            vehicle_type="冷蔵軽貨物",
            price=19000,
            company_name="テスト運送",
            contact_name="山田",
            phone_number="09012345678",
        )

        with patch("apps.api.app.services.supabase.insert_row", side_effect=lambda _client, _table, payload: payload):
            payload = create_liff_job(object(), form)

        self.assertEqual(payload["source_type"], "liff_form")
        self.assertEqual(payload["posting_type"], "other")
        self.assertEqual(payload["job_category"], "referral_request")
        self.assertEqual(payload["title"], "定期案件の紹介依頼")
        self.assertIn("老舗のお弁当", payload["free_text"])
        self.assertEqual(payload["target_area"], "都内中心")
        self.assertIsNone(payload["pickup_location"])
        self.assertIsNone(payload["delivery_location"])
        self.assertEqual(payload["fare_calc_status"], "not_applicable")
        self.assertEqual(payload["fare_calc_note"], "積地・卸地を指定しない案件のため")
        self.assertEqual(payload["status"], "open")

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
            price=17000,
            distance_km=92.4,
            distance_text="約92km",
            distance_source="google_maps",
            posted_fare_yen=17000,
            standard_fare_yen=13850,
            fare_ratio_percent=122.7,
            fare_ratio_text="123%",
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
        self.assertEqual(payload["posted_fare_yen"], 17000)
        self.assertEqual(payload["standard_fare_yen"], 13850)
        self.assertEqual(payload["fare_ratio_percent"], 122.7)
        self.assertEqual(payload["fare_ratio_text"], "123%")
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
        fare_sql = Path("supabase/migrations/015_jobs_posted_fare_yen.sql").read_text(encoding="utf-8")
        other_sql = Path("supabase/migrations/016_jobs_other_posting_fields.sql").read_text(encoding="utf-8")

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
        self.assertIn("add column if not exists posted_fare_yen integer", fare_sql)
        self.assertIn("add column if not exists fare_ratio_text text", fare_sql)
        self.assertIn("add column if not exists posting_type text", other_sql)
        self.assertIn("add column if not exists title text", other_sql)
        self.assertIn("driver_recruitment", other_sql)
        self.assertIn("referral_request", other_sql)

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
