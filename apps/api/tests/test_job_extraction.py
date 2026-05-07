from __future__ import annotations

import unittest
from datetime import date

from apps.api.app.services.message_classifier import (
    build_line_job_payload,
    enrich_line_job_contact_fields,
    postprocess_job_fields,
)
from apps.api.app.services.supabase import is_job_owner_report


REAL_LINE_SAMPLE = (
    "本日、大阪府枚方市積み→5月2日埼玉県日高市下ろし\n"
    "4t 低予算に対応出来る方いませんか？"
)


class JobExtractionTest(unittest.TestCase):
    def test_postprocess_route_dates_and_prefectures(self) -> None:
        result = postprocess_job_fields(
            REAL_LINE_SAMPLE,
            {"missing_fields": []},
            reference_date=date(2026, 5, 2),
        )

        self.assertEqual(result["pickup_location"], "大阪府枚方市")
        self.assertEqual(result["pickup_prefecture"], "大阪府")
        self.assertEqual(result["delivery_location"], "埼玉県日高市")
        self.assertEqual(result["delivery_prefecture"], "埼玉県")
        self.assertEqual(result["scheduled_date"], "2026-05-02")
        self.assertEqual(result["delivery_date"], "2026-05-02")
        self.assertEqual(result["vehicle_type"], "4t")
        self.assertEqual(result["budget_note"], "低予算")
        self.assertIsNone(result["price"])
        self.assertIn("price", result["missing_fields"])

    def test_line_job_payload_uses_received_date_for_honjitsu(self) -> None:
        payload = build_line_job_payload(
            line_message={
                "id": "line-message-id",
                "source_group_id": "group-id",
                "source_user_id": "user-id",
                "source_message_id": "source-message-id",
                "received_at": "2026-05-01T14:30:00+00:00",
            },
            raw_text=REAL_LINE_SAMPLE,
            message_type="job_request",
            confidence=0.82,
        )

        self.assertEqual(payload["pickup_location"], "大阪府枚方市")
        self.assertEqual(payload["pickup_prefecture"], "大阪府")
        self.assertEqual(payload["delivery_location"], "埼玉県日高市")
        self.assertEqual(payload["delivery_prefecture"], "埼玉県")
        self.assertEqual(payload["scheduled_date"], "2026-05-01")
        self.assertEqual(payload["delivery_date"], "2026-05-02")
        self.assertEqual(payload["vehicle_type"], "4t")
        self.assertEqual(payload["budget_note"], "低予算")
        self.assertIsNone(payload["price"])
        self.assertIn("price", payload["missing_fields"])

    def test_contact_phone_from_text_wins(self) -> None:
        payload = enrich_line_job_contact_fields(
            {
                "raw_text": "大阪府枚方市積み→埼玉県日高市下ろし 090-1234-5678",
                "source_user_id": "Uowner",
                "review_required": False,
            },
            line_user={
                "display_name": "投稿者A",
                "phone_number": "080-0000-0000",
                "company_name": "登録会社",
                "contact_name": "登録担当",
            },
        )

        self.assertEqual(payload["created_by_display_name"], "投稿者A")
        self.assertEqual(payload["contact_line_user_id"], "Uowner")
        self.assertEqual(payload["contact_display_name"], "投稿者A")
        self.assertEqual(payload["contact_phone"], "090-1234-5678")
        self.assertEqual(payload["contact_method"], "phone")
        self.assertFalse(payload["contact_missing"])

    def test_contact_missing_without_text_or_registered_phone(self) -> None:
        payload = enrich_line_job_contact_fields(
            {
                "raw_text": "大阪府枚方市積み→埼玉県日高市下ろし",
                "source_user_id": "Uowner",
                "review_required": False,
            },
            line_user={"display_name": "投稿者A"},
        )

        self.assertIsNone(payload["contact_phone"])
        self.assertEqual(payload["contact_method"], "group_reply_or_admin")
        self.assertTrue(payload["contact_missing"])
        self.assertTrue(payload["review_required"])

    def test_owner_report_detection(self) -> None:
        self.assertTrue(
            is_job_owner_report(
                {"created_by_line_user_id": "Uowner", "source_user_id": "Uother"},
                "Uowner",
            )
        )
        self.assertFalse(
            is_job_owner_report(
                {"created_by_line_user_id": "Uowner", "source_user_id": "Uowner"},
                "Uother",
            )
        )


if __name__ == "__main__":
    unittest.main()
