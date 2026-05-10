from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]


class FrontendCompanySearchContractsTest(unittest.TestCase):
    def test_company_results_are_collapsed_until_details_are_opened(self) -> None:
        source = (ROOT / "apps/web/src/pages/CompanySearchPage.tsx").read_text(encoding="utf-8")

        self.assertIn("const [openIndex, setOpenIndex]", source)
        self.assertIn("isOpen={openIndex === index}", source)
        self.assertIn("setOpenIndex((current) => (current === index ? null : index))", source)
        self.assertIn("className=\"company-card__summary-button\"", source)
        self.assertIn("company-card__company", source)
        self.assertIn("{isOpen ? (", source)
        self.assertIn("詳細を見る", source)
        self.assertIn("閉じる", source)

    def test_company_details_keep_contact_links_and_fields(self) -> None:
        source = (ROOT / "apps/web/src/pages/CompanySearchPage.tsx").read_text(encoding="utf-8")

        for label in ["会社名", "役職", "氏名", "ローマ字", "TEL", "携帯", "FAX", "メール", "郵便番号", "地域", "住所", "支店", "URL", "LINE URL", "Notes"]:
            self.assertIn(f'label="{label}"', source)
        self.assertIn("phoneHref(item.tel)", source)
        self.assertIn("phoneHref(item.mobile)", source)
        self.assertIn("mailHref(item.email)", source)
        self.assertIn("externalHref(item.url)", source)
        self.assertIn("externalHref(item.line_url)", source)
        self.assertIn("return normalized ? `tel:${normalized}` : null", source)
        self.assertIn("return trimmed ? `mailto:${trimmed}` : null", source)

    def test_company_search_empty_result_message_remains(self) -> None:
        source = (ROOT / "apps/web/src/pages/CompanySearchPage.tsx").read_text(encoding="utf-8")

        self.assertIn("該当する企業が見つかりませんでした", source)


if __name__ == "__main__":
    unittest.main()
