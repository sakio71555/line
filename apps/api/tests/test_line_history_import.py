from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from scripts.import_line_history import (
    HistoryImporter,
    HistoryMessage,
    SOURCE_TYPE,
    classify_history_message,
    extract_history_dates,
    history_message_hash,
    parse_history_text,
    title_text,
)


class LineHistoryImportTest(unittest.TestCase):
    def test_parse_date_lines_and_multiline_messages(self) -> None:
        messages = parse_history_text(
            """2026.05.01 金曜日
09:27 タカオ お世話になります。
本日、大阪府枚方市積み→5月2日埼玉県日高市下ろし
4t 低予算に対応出来る方いませんか？
10:15 r.shimano メンバーさんに対応頂きました。
ありがとうございました。
"""
        )

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].history_date.isoformat(), "2026-05-01")
        self.assertEqual(messages[0].history_time.isoformat(timespec="minutes"), "09:27")
        self.assertEqual(messages[0].sender_name, "タカオ")
        self.assertIn("大阪府枚方市", messages[0].raw_text)
        self.assertIn("ありがとうございました。", messages[1].raw_text)

    def test_history_classification_examples(self) -> None:
        self.assertEqual(classify_history_message("【軽貨物案件】\n本日 大阪府枚方市積み→埼玉県日高市下ろし").message_type, "job_request")
        self.assertEqual(classify_history_message("富山県魚津市で軽バンが空車となりました。").message_type, "vehicle_availability")
        self.assertEqual(classify_history_message("軽幌車増車いたしました").message_type, "vehicle_availability")
        self.assertEqual(classify_history_message("メンバーさんに対応頂きました。ありがとうございました。").message_type, "job_closed")

    def test_history_non_job_events_are_not_jobs(self) -> None:
        self.assertEqual(classify_history_message("新しいノートを作成しました").message_type, "note_event")
        self.assertEqual(classify_history_message("アナウンスしました").message_type, "note_event")
        self.assertEqual(classify_history_message("メッセージの送信を取り消しました").message_type, "unsend_event")
        self.assertEqual(classify_history_message("佐藤さんをグループに招待しました").message_type, "member_event")
        self.assertEqual(classify_history_message("佐藤さんをグループから削除しました").message_type, "member_event")
        self.assertEqual(classify_history_message("産業廃棄物収集運搬事業部の小島も招待致します。").message_type, "member_event")
        self.assertEqual(classify_history_message("グループ招待").message_type, "member_event")
        self.assertEqual(classify_history_message("codex-phase37-1777644740-1388f3f1.pdf").message_type, "attachment")
        self.assertEqual(classify_history_message("画像").message_type, "attachment")
        self.assertEqual(classify_history_message("090-1234-5678").message_type, "contact_note")
        self.assertNotEqual(classify_history_message("@All 懇親会PDF 申込フォーム").message_type, "job_request")
        self.assertNotEqual(classify_history_message("https://docs.google.com/forms/d/e/example").message_type, "job_request")

    def test_history_status_update_examples(self) -> None:
        self.assertIn(classify_history_message("自社で見つかったそうです").message_type, {"job_closed", "job_completed"})
        self.assertIn(classify_history_message("配車完了しました").message_type, {"job_closed", "job_completed"})
        self.assertEqual(classify_history_message("現状の残り台数 3台です").message_type, "status_update")
        self.assertEqual(classify_history_message("残り2台です。").message_type, "status_update")
        self.assertEqual(classify_history_message("5/3のみ\n25,000円\n7.5%あり\nに上がりました。").message_type, "status_update")

    def test_history_work_job_examples(self) -> None:
        self.assertEqual(classify_history_message("明日 13:00作業開始 搬入助手作業").message_type, "work_job")
        self.assertEqual(classify_history_message("引越し助手を探しています").message_type, "work_job")
        self.assertEqual(classify_history_message("【引越作業助手】").message_type, "work_job")
        self.assertEqual(classify_history_message("本日これから野田市〜東京都港区まで走れる軽貨物を探しています。").message_type, "job_request")
        self.assertEqual(classify_history_message("現在埼玉県川越方面で軽貨物常温バンの案件を探しております。").message_type, "vehicle_availability")
        self.assertEqual(classify_history_message("ドライバー情報\n名古屋市中区54歳 男性\n軽バン有り").message_type, "vehicle_availability")

    def test_history_date_extraction_uses_posted_date(self) -> None:
        message_date = parse_history_text("2026.05.01 金曜日\n09:27 タカオ 本日積み→5/2下ろし\n")[0].history_date
        dates = extract_history_dates("本日、大阪府枚方市積み→5月2日埼玉県日高市下ろし", message_date)

        self.assertEqual(dates["pickup_date"], "2026-05-01")
        self.assertEqual(dates["delivery_date"], "2026-05-02")
        self.assertFalse(dates["date_needs_review"])

    def test_ambiguous_dates_need_review(self) -> None:
        dates = extract_history_dates("5月下旬以降 毎週月曜 決まり次第", parse_history_text("2026.05.01 金曜日\n09:27 A test\n")[0].history_date)

        self.assertIsNone(dates["pickup_date"])
        self.assertTrue(dates["date_needs_review"])
        self.assertTrue(dates["recurring"])
        self.assertIn("5月下旬", dates["schedule_text"])

    def test_period_date_keeps_schedule_text(self) -> None:
        dates = extract_history_dates("3/20（金）〜4月初旬頃まで 7:30〜16:30", parse_history_text("2026.03.01 日曜日\n09:27 A test\n")[0].history_date)

        self.assertEqual(dates["pickup_date"], "2026-03-20")
        self.assertTrue(dates["date_needs_review"])
        self.assertIn("3/20", dates["schedule_text"])

    def test_non_job_date_is_not_extracted_in_dry_run(self) -> None:
        messages = parse_history_text("2026.05.01 金曜日\n09:27 A @All 5/2 懇親会PDF 申込フォーム\n")
        importer = HistoryImporter(dry_run=True, import_batch_id="batch-id", client=None)
        output = io.StringIO()
        with redirect_stdout(output):
            summary = importer.import_messages(messages)

        self.assertEqual(summary.ignored_events, 1)
        self.assertIn('"pickup_date": null', output.getvalue())

    def test_title_text_does_not_stop_at_greeting(self) -> None:
        title = title_text(
            "お世話になります。\n"
            "本日、大阪府枚方市積み→5月2日埼玉県日高市下ろし\n"
            "4t 低予算に対応出来る方いませんか？"
        )

        self.assertNotEqual(title, "お世話になります。")
        self.assertIn("大阪府枚方市", title)

    def test_dry_run_does_not_save_to_db_and_deduplicates(self) -> None:
        messages = parse_history_text(
            """2026.05.01 金曜日
09:27 タカオ 本日、大阪府枚方市積み→5月2日埼玉県日高市下ろし
09:27 タカオ 本日、大阪府枚方市積み→5月2日埼玉県日高市下ろし
"""
        )
        importer = HistoryImporter(dry_run=True, import_batch_id="batch-id", client=None)
        output = io.StringIO()
        with redirect_stdout(output):
            summary = importer.import_messages(messages)

        self.assertEqual(summary.messages, 2)
        self.assertEqual(summary.jobs, 1)
        self.assertEqual(summary.duplicates, 1)
        self.assertIn('"message_type": "job_request"', output.getvalue())
        self.assertEqual(summary.message_type_counts, {"job_request": 1})

    def test_history_import_source_type_is_preserved(self) -> None:
        self.assertEqual(SOURCE_TYPE, "line_history_import")

    def test_dry_run_prints_type_counts_and_unknown_samples(self) -> None:
        messages = parse_history_text("2026.05.01 金曜日\n09:27 A 雑談だけです\n")
        importer = HistoryImporter(dry_run=True, import_batch_id="batch-id", client=None)
        output = io.StringIO()
        with redirect_stdout(output):
            summary = importer.import_messages(messages)
            from scripts.import_line_history import print_summary

            print_summary(summary, import_batch_id="batch-id", dry_run=True)

        self.assertIn("message_type_counts:", output.getvalue())
        self.assertIn("unknown_samples:", output.getvalue())

    def test_history_hash_is_stable(self) -> None:
        message = HistoryMessage(
            history_date=parse_history_text("2026.05.01 金曜日\n09:27 A test\n")[0].history_date,
            history_time=parse_history_text("2026.05.01 金曜日\n09:27 A test\n")[0].history_time,
            sender_name="A",
            raw_text="test",
        )

        self.assertEqual(history_message_hash(message), history_message_hash(message))


if __name__ == "__main__":
    unittest.main()
