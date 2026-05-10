from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]


class FrontendOtherJobContractsTest(unittest.TestCase):
    def test_job_card_has_body_preview_and_full_body_fields(self) -> None:
        source = (ROOT / "apps/web/src/components/JobCard.tsx").read_text(encoding="utf-8")
        css = (ROOT / "apps/web/src/styles/main.css").read_text(encoding="utf-8")

        self.assertIn("job-card__body-preview", source)
        self.assertIn("jobBodyText", source)
        self.assertIn("案件本文", source)
        self.assertIn("本文未入力", source)
        self.assertIn("備考なし", source)
        self.assertIn("white-space: pre-wrap", css)
        self.assertIn("-webkit-line-clamp: 4", css)

    def test_job_card_body_priority_differs_by_posting_type(self) -> None:
        source = (ROOT / "apps/web/src/components/JobCard.tsx").read_text(encoding="utf-8")
        other_start = source.index("const candidates = isOtherPosting(job)")
        other_free_text = source.index("job.free_text", other_start)
        other_notes = source.index("job.notes", other_start)
        normal_start = source.index(": [", other_start)
        normal_notes = source.index("job.notes", normal_start)
        normal_free_text = source.index("job.free_text", normal_start)

        self.assertLess(other_free_text, other_notes)
        self.assertLess(normal_notes, normal_free_text)

    def test_submission_form_has_delivery_and_other_modes(self) -> None:
        source = (ROOT / "apps/web/src/pages/JobSubmissionPage.tsx").read_text(encoding="utf-8")

        self.assertIn("通常配送案件", source)
        self.assertIn("その他案件", source)
        self.assertIn("タイトル", source)
        self.assertIn("案件本文", source)
        self.assertIn("target_area", source)

    def test_job_list_status_tabs_use_operational_status_groups(self) -> None:
        source = (ROOT / "apps/web/src/hooks/useJobs.ts").read_text(encoding="utf-8")

        self.assertIn('const ACTIVE_STATUSES = ["open"]', source)
        self.assertIn('const ENDED_STATUSES = ["assigned", "closed", "completed", "cancelled"]', source)
        self.assertIn('.is("deleted_at", null)', source)

    def test_status_labels_and_line_outside_admin_guidance_are_explicit(self) -> None:
        types_source = (ROOT / "apps/web/src/types/job.ts").read_text(encoding="utf-8")
        admin_source = (ROOT / "apps/web/src/pages/AdminJobsPage.tsx").read_text(encoding="utf-8")

        self.assertIn('assigned: "手配完了"', types_source)
        self.assertIn('closed: "募集終了"', types_source)
        self.assertIn('deleted: "削除済み"', types_source)
        self.assertIn("管理画面はLINEアプリ内から開いてください", admin_source)
        self.assertIn("通常ブラウザでは管理操作できません", admin_source)

    def test_admin_full_location_fields_are_readonly_generated_previews(self) -> None:
        source = (ROOT / "apps/web/src/components/AdminJobEditor.tsx").read_text(encoding="utf-8")

        self.assertIn("const pickupLocationPreview = buildLocation", source)
        self.assertIn("const deliveryLocationPreview =", source)
        self.assertIn("value={pickupLocationPreview}", source)
        self.assertIn("value={deliveryLocationPreview}", source)
        self.assertIn("readOnly", source)
        self.assertIn("積地全体（自動）", source)
        self.assertIn("卸地全体（自動）", source)
        self.assertIn("pickup_location: pickupLocation || form.pickup_location || null", source)
        self.assertIn("delivery_location: deliveryLocation || form.delivery_location || null", source)


if __name__ == "__main__":
    unittest.main()
