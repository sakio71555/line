from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]


class FrontendAdminConsoleContractsTest(unittest.TestCase):
    def test_admin_console_route_is_direct_and_not_in_normal_tabbar(self) -> None:
        source = (ROOT / "apps/web/src/App.tsx").read_text(encoding="utf-8")

        self.assertIn('window.location.pathname === "/admin-console"', source)
        self.assertIn('admin_console: "admin_console"', source)
        self.assertIn("return <AdminConsolePage />", source)
        self.assertNotIn(">PC運営者管理ページ</button>", source)

    def test_admin_console_page_has_login_filters_details_and_actions(self) -> None:
        source = (ROOT / "apps/web/src/pages/AdminConsolePage.tsx").read_text(encoding="utf-8")

        self.assertIn('type="password"', source)
        self.assertIn("管理者パスワードまたはトークン", source)
        self.assertIn("全案件一覧", source)
        self.assertIn("status", source)
        self.assertIn("posting_type", source)
        self.assertIn("job_category", source)
        self.assertIn("削除済みのみ", source)
        self.assertIn("募集中のみ", source)
        self.assertIn("終了案件のみ", source)
        self.assertIn("案件詳細", source)
        self.assertIn("論理削除", source)
        self.assertIn("復元", source)
        self.assertIn("企業検索を開く", source)

    def test_admin_console_api_sends_admin_header_without_frontend_secret_literals(self) -> None:
        source = (ROOT / "apps/web/src/lib/adminConsoleApi.ts").read_text(encoding="utf-8")

        self.assertIn('"X-Admin-Token": auth.token', source)
        self.assertIn("/admin-console/jobs", source)
        self.assertIn("/admin-console/vehicle-availabilities", source)
        self.assertNotIn("ADMIN_CONSOLE_TOKEN=", source)
        self.assertNotIn("ADMIN_CONSOLE_PASSWORD=", source)


if __name__ == "__main__":
    unittest.main()
