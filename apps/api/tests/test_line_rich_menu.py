from __future__ import annotations

import unittest

from scripts.create_line_rich_menu import build_rich_menu, redact_liff_urls


class LineRichMenuTest(unittest.TestCase):
    def test_builds_six_area_rich_menu(self) -> None:
        rich_menu = build_rich_menu(liff_id="test-liff-id", liff_base_url=None)
        areas = rich_menu["areas"]

        self.assertEqual(rich_menu["size"], {"width": 2500, "height": 1686})
        self.assertEqual(rich_menu["name"], "transport-main-menu")
        self.assertEqual(rich_menu["chatBarText"], "メニュー")
        self.assertEqual(len(areas), 6)
        self.assertEqual(areas[0]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=post")
        self.assertEqual(areas[1]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=vehicle")
        self.assertEqual(areas[2]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=list")
        self.assertEqual(areas[3]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=admin")
        self.assertEqual(areas[4]["action"], {"type": "message", "text": "使い方"})
        self.assertEqual(areas[5]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=companies")

    def test_dry_run_redacts_liff_id(self) -> None:
        rich_menu = build_rich_menu(liff_id="test-liff-id", liff_base_url=None)
        redacted = redact_liff_urls(rich_menu)

        self.assertEqual(redacted["areas"][0]["action"]["uri"], "https://liff.line.me/{LIFF_ID}?tab=post")
        self.assertNotIn("test-liff-id", str(redacted))


if __name__ == "__main__":
    unittest.main()
