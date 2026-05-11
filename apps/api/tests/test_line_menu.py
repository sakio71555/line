from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from apps.api.app.routers.line_webhook import process_classified_message
from apps.api.app.services.line_push import LinePushError
from apps.api.app.services.line_reply import build_help_text, build_liff_url, build_menu_flex_message
from apps.api.app.services.message_classifier import classify_text
from apps.api.app.services.supabase import create_liff_session


class LineMenuTest(unittest.TestCase):
    def test_menu_keywords_are_classified_as_menu_request(self) -> None:
        for keyword in ["メニュー", "案件投稿", "空車登録", "案件一覧", "フォーム", "企業検索"]:
            with self.subTest(keyword=keyword):
                self.assertEqual(classify_text(keyword).message_type, "menu_request")

    def test_help_keywords_are_classified_as_help_request(self) -> None:
        for keyword in ["使い方", "ヘルプ", "help", "操作方法", "利用方法"]:
            with self.subTest(keyword=keyword):
                self.assertEqual(classify_text(keyword).message_type, "help_request")

    def test_existing_classification_examples_still_route(self) -> None:
        self.assertEqual(
            classify_text("富山県魚津市で軽バンが空車となりました。").message_type,
            "vehicle_availability",
        )
        self.assertEqual(
            classify_text("本日、大阪府枚方市積み→5月2日埼玉県日高市下ろし\n4t 低予算").message_type,
            "job_request",
        )
        self.assertEqual(
            classify_text("メンバーさんに対応頂きました。ありがとうございました。").message_type,
            "job_closed",
        )

    def test_menu_liff_urls_are_generated_from_liff_id(self) -> None:
        settings = SimpleNamespace(liff_base_url=None, liff_id="test-liff-id")

        self.assertEqual(
            build_liff_url(settings, "post"),
            "https://liff.line.me/test-liff-id?tab=post",
        )

    def test_menu_liff_urls_are_generated_from_base_url(self) -> None:
        settings = SimpleNamespace(liff_base_url="https://liff.line.me/test-liff-id?foo=bar", liff_id=None)

        self.assertEqual(
            build_liff_url(settings, "vehicle"),
            "https://liff.line.me/test-liff-id?foo=bar&tab=vehicle",
        )

    def test_menu_liff_url_includes_session_id(self) -> None:
        settings = SimpleNamespace(liff_base_url=None, liff_id="test-liff-id")

        self.assertEqual(
            build_liff_url(settings, "post", session_id="session-123"),
            "https://liff.line.me/test-liff-id?tab=post&session_id=session-123",
        )

    def test_menu_flex_message_contains_expected_buttons(self) -> None:
        settings = SimpleNamespace(liff_base_url=None, liff_id="test-liff-id")
        message = build_menu_flex_message(settings, session_id="session-123")
        buttons = message["contents"]["footer"]["contents"]

        self.assertEqual(message["type"], "flex")
        self.assertEqual(message["altText"], "案件登録メニュー")
        self.assertEqual(len(buttons), 5)
        self.assertEqual(
            [button["action"]["label"] for button in buttons],
            ["案件を投稿", "空車を登録", "案件一覧を見る", "管理画面を開く", "企業検索"],
        )
        self.assertEqual(buttons[0]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=post&session_id=session-123")
        self.assertEqual(buttons[1]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=vehicle&session_id=session-123")
        self.assertEqual(buttons[2]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=list&session_id=session-123")
        self.assertEqual(buttons[3]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=admin&session_id=session-123")
        self.assertEqual(buttons[4]["action"]["uri"], "https://liff.line.me/test-liff-id?tab=companies&session_id=session-123")

    def test_group_menu_request_pushes_private_menu_without_creating_domain_records(self) -> None:
        settings = object()
        with (
            patch("apps.api.app.routers.line_webhook.create_liff_session", return_value={"session_id": "session-123"}) as create_session,
            patch("apps.api.app.routers.line_webhook.push_menu_message") as push_menu,
            patch("apps.api.app.routers.line_webhook.reply_menu_message") as reply_menu,
            patch("apps.api.app.routers.line_webhook.create_job_from_line_message") as create_job,
            patch("apps.api.app.routers.line_webhook.create_vehicle_availability") as create_vehicle,
            patch("apps.api.app.routers.line_webhook.create_status_update_from_line_message") as create_status,
        ):
            did_process = process_classified_message(
                supabase=object(),
                line_message={
                    "id": "line-message-id",
                    "raw_text": "メニュー",
                    "source_group_id": "Cgroup",
                    "source_user_id": "Uuser",
                },
                line_user=None,
                message_type="menu_request",
                settings=settings,
                reply_token="reply-token",
            )

        self.assertTrue(did_process)
        create_session.assert_called_once()
        push_menu.assert_called_once_with(settings, "Uuser", session_id="session-123")
        reply_menu.assert_not_called()
        create_job.assert_not_called()
        create_vehicle.assert_not_called()
        create_status.assert_not_called()

    def test_direct_chat_menu_request_replies_in_place_without_session(self) -> None:
        settings = object()
        with (
            patch("apps.api.app.routers.line_webhook.create_liff_session") as create_session,
            patch("apps.api.app.routers.line_webhook.push_menu_message") as push_menu,
            patch("apps.api.app.routers.line_webhook.reply_menu_message") as reply_menu,
        ):
            did_process = process_classified_message(
                supabase=object(),
                line_message={
                    "id": "line-message-id",
                    "raw_text": "メニュー",
                    "source_group_id": "Uuser",
                    "source_user_id": "Uuser",
                },
                line_user=None,
                message_type="menu_request",
                settings=settings,
                reply_token="reply-token",
            )

        self.assertTrue(did_process)
        create_session.assert_not_called()
        push_menu.assert_not_called()
        reply_menu.assert_called_once_with(settings, "reply-token", session_id=None)

    def test_help_text_explains_main_operations(self) -> None:
        text = build_help_text()

        for phrase in ["案件を見る", "案件を出す", "空車を登録", "自分の投稿を管理", "企業検索"]:
            self.assertIn(phrase, text)

    def test_group_help_request_pushes_private_help_without_creating_domain_records(self) -> None:
        settings = object()
        with (
            patch("apps.api.app.routers.line_webhook.push_help_message") as push_help,
            patch("apps.api.app.routers.line_webhook.reply_help_message") as reply_help,
            patch("apps.api.app.routers.line_webhook.create_job_from_line_message") as create_job,
            patch("apps.api.app.routers.line_webhook.create_vehicle_availability") as create_vehicle,
            patch("apps.api.app.routers.line_webhook.create_status_update_from_line_message") as create_status,
        ):
            did_process = process_classified_message(
                supabase=object(),
                line_message={
                    "id": "line-message-id",
                    "raw_text": "使い方",
                    "source_group_id": "Cgroup",
                    "source_user_id": "Uuser",
                },
                line_user=None,
                message_type="help_request",
                settings=settings,
                reply_token="reply-token",
            )

        self.assertTrue(did_process)
        push_help.assert_called_once_with(settings, "Uuser")
        reply_help.assert_not_called()
        create_job.assert_not_called()
        create_vehicle.assert_not_called()
        create_status.assert_not_called()

    def test_direct_chat_help_request_replies_in_place(self) -> None:
        settings = object()
        with (
            patch("apps.api.app.routers.line_webhook.push_help_message") as push_help,
            patch("apps.api.app.routers.line_webhook.reply_help_message") as reply_help,
        ):
            did_process = process_classified_message(
                supabase=object(),
                line_message={
                    "id": "line-message-id",
                    "raw_text": "使い方",
                    "source_group_id": "Uuser",
                    "source_user_id": "Uuser",
                },
                line_user=None,
                message_type="help_request",
                settings=settings,
                reply_token="reply-token",
            )

        self.assertTrue(did_process)
        push_help.assert_not_called()
        reply_help.assert_called_once_with(settings, "reply-token")

    def test_group_menu_push_failure_is_recorded_without_raising(self) -> None:
        settings = object()
        supabase = object()
        with (
            patch("apps.api.app.routers.line_webhook.create_liff_session", return_value={"session_id": "session-123"}),
            patch(
                "apps.api.app.routers.line_webhook.push_menu_message",
                side_effect=LinePushError("LINE push request failed with status 403"),
            ),
            patch("apps.api.app.routers.line_webhook.mark_line_message_processed") as mark_processed,
        ):
            did_process = process_classified_message(
                supabase=supabase,
                line_message={
                    "id": "line-message-id",
                    "raw_text": "メニュー",
                    "source_group_id": "Cgroup",
                    "source_user_id": "Uuser",
                },
                line_user=None,
                message_type="menu_request",
                settings=settings,
                reply_token="reply-token",
            )

        self.assertTrue(did_process)
        mark_processed.assert_called_once_with(
            supabase,
            "line-message-id",
            processing_error="LinePushError",
        )

    def test_liff_session_keeps_group_id_but_not_direct_user_id(self) -> None:
        def fake_insert(_client, _table, payload):
            return payload

        with patch("apps.api.app.services.supabase.insert_row", side_effect=fake_insert):
            group_session = create_liff_session(
                object(),
                {
                    "id": "line-message-id",
                    "source_group_id": "Cgroup",
                    "source_user_id": "Uuser",
                },
            )
            direct_session = create_liff_session(
                object(),
                {
                    "id": "line-message-id",
                    "source_group_id": "Uuser",
                    "source_user_id": "Uuser",
                },
            )

        self.assertEqual(group_session["source_group_id"], "Cgroup")
        self.assertIsNone(direct_session["source_group_id"])


if __name__ == "__main__":
    unittest.main()
