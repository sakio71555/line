from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.app.services.message_classifier import (
    build_line_job_payload,
    build_vehicle_availability_payload,
    classify_text,
    extract_route_locations,
    extract_phone_numbers,
    proposed_status_from_message_type,
)
from apps.api.app.services.supabase import (
    SupabaseRestClient,
    get_supabase_client,
    insert_row,
)

SOURCE_TYPE = "line_history_import"
JST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class HistoryMessage:
    history_date: date
    history_time: time
    sender_name: str
    raw_text: str

    @property
    def posted_at(self) -> datetime:
        return datetime.combine(self.history_date, self.history_time, tzinfo=JST)


@dataclass
class ImportSummary:
    messages: int = 0
    jobs: int = 0
    vehicle_availabilities: int = 0
    status_updates: int = 0
    ignored_events: int = 0
    duplicates: int = 0
    message_type_counts: dict[str, int] | None = None
    unknown_samples: list[dict[str, str]] | None = None


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    text = Path(args.input_file).read_text(encoding="utf-8")
    messages = parse_history_text(text)
    import_batch_id = str(uuid.uuid4())
    importer = HistoryImporter(
        dry_run=args.dry_run,
        import_batch_id=import_batch_id,
        client=None if args.dry_run else get_supabase_client(),
    )
    summary = importer.import_messages(messages)
    print_summary(summary, import_batch_id=import_batch_id, dry_run=args.dry_run)
    return 0


def parse_args(argv: Optional[list[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import exported LINE group history into Supabase.")
    parser.add_argument("input_file", help="LINE過去ログのtxtファイル")
    parser.add_argument("--dry-run", action="store_true", help="DB保存せず分類結果と件数だけ表示します")
    return parser.parse_args(argv)


class HistoryImporter:
    def __init__(
        self,
        *,
        dry_run: bool,
        import_batch_id: str,
        client: Optional[SupabaseRestClient],
    ) -> None:
        self.dry_run = dry_run
        self.import_batch_id = import_batch_id
        self.client = client
        self.seen_hashes: set[str] = set()

    def import_messages(self, messages: list[HistoryMessage]) -> ImportSummary:
        summary = ImportSummary(messages=len(messages))
        summary.message_type_counts = {}
        summary.unknown_samples = []
        for message in messages:
            decision = classify_history_message(message.raw_text)
            history_hash = history_message_hash(message)
            if history_hash in self.seen_hashes or (not self.dry_run and self.exists(history_hash)):
                summary.duplicates += 1
                continue
            self.seen_hashes.add(history_hash)
            summary.message_type_counts[decision.message_type] = summary.message_type_counts.get(decision.message_type, 0) + 1
            if decision.message_type == "unknown" and len(summary.unknown_samples) < 20:
                summary.unknown_samples.append(
                    {
                        "posted_at": message.posted_at.isoformat(),
                        "sender_name": message.sender_name,
                        "text": title_text(message.raw_text),
                    }
                )

            date_info = extract_history_dates(message.raw_text, message.history_date) if should_extract_dates(decision.message_type) else empty_date_info()
            if self.dry_run:
                print_dry_run_item(message, decision.message_type, date_info)
                increment_summary(summary, decision.message_type)
                continue

            line_message = self.save_line_message(message, decision, history_hash)
            try:
                self.save_domain_record(message, line_message, decision, history_hash, date_info)
                increment_summary(summary, decision.message_type)
            except Exception:
                self.mark_processing_error(line_message, "HistoryImportDomainSaveError")
                summary.ignored_events += 1
        return summary

    def exists(self, history_hash: str) -> bool:
        if not self.client:
            return False
        response = httpx.get(
            f"{self.client.rest_url}/line_messages",
            params={
                "select": "id",
                "history_message_hash": f"eq.{history_hash}",
                "limit": "1",
            },
            headers=self.client.headers,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return bool(data)

    def save_line_message(
        self,
        message: HistoryMessage,
        decision: "HistoryClassification",
        history_hash: str,
    ) -> dict[str, Any]:
        assert self.client is not None
        return insert_row(
            self.client,
            "line_messages",
            {
                "source_type": SOURCE_TYPE,
                "source_group_id": None,
                "source_user_id": None,
                "source_display_name": message.sender_name,
                "source_message_id": history_hash,
                "event_type": "message",
                "message_type": decision.message_type,
                "raw_text": message.raw_text,
                "attachment_type": decision.attachment_type,
                "attachment_file_name": decision.attachment_file_name,
                "attachment_message_id": history_hash if decision.message_type == "attachment" else None,
                "is_unsent": decision.message_type == "unsend_event",
                "received_at": message.posted_at.isoformat(),
                "posted_at": message.posted_at.isoformat(),
                "history_date": message.history_date.isoformat(),
                "history_time": message.history_time.isoformat(timespec="minutes"),
                "classification_confidence": decision.confidence,
                "classification_reason": decision.reason,
                "import_batch_id": self.import_batch_id,
                "history_message_hash": history_hash,
            },
        )

    def save_domain_record(
        self,
        message: HistoryMessage,
        line_message: dict[str, Any],
        decision: "HistoryClassification",
        history_hash: str,
        date_info: dict[str, Any],
    ) -> None:
        if not self.client:
            return
        if decision.message_type in {"job_request", "regular_job", "work_job"}:
            payload = build_line_job_payload(
                line_message={
                    "id": line_message.get("id"),
                    "source_group_id": None,
                    "source_user_id": None,
                    "source_message_id": history_hash,
                    "received_at": message.posted_at.isoformat(),
                },
                raw_text=message.raw_text,
                message_type=decision.message_type,
                confidence=decision.confidence,
                line_user={"display_name": message.sender_name},
            )
            payload.update(history_common_fields(message, history_hash, self.import_batch_id, date_info))
            payload["source_type"] = SOURCE_TYPE
            payload["created_by_display_name"] = message.sender_name
            payload["contact_display_name"] = message.sender_name
            insert_row(self.client, "jobs", payload)
            return

        if decision.message_type == "vehicle_availability":
            payload = build_vehicle_availability_payload(
                line_message={"id": line_message.get("id"), "source_group_id": None, "source_user_id": None},
                raw_text=message.raw_text,
                confidence=decision.confidence,
            )
            payload.update(
                {
                    "source_type": SOURCE_TYPE,
                    "source_line_message_id": line_message.get("id"),
                    "available_date": date_info.get("pickup_date"),
                    "notes": message.raw_text,
                    "contact_name": message.sender_name,
                    "contact_phone": first_phone(message.raw_text),
                    "posted_at": message.posted_at.isoformat(),
                    "import_batch_id": self.import_batch_id,
                    "history_message_hash": history_hash,
                }
            )
            insert_row(self.client, "vehicle_availabilities", payload)
            return

        if decision.message_type in {"job_closed", "job_completed", "status_update", "availability_update"}:
            update_type, proposed_status = proposed_status_for_history(decision.message_type)
            insert_row(
                self.client,
                "job_status_updates",
                {
                    "source_type": SOURCE_TYPE,
                    "source_line_message_id": line_message.get("id"),
                    "source_group_id": None,
                    "source_user_id": None,
                    "source_message_id": history_hash,
                    "raw_text": message.raw_text,
                    "update_type": update_type,
                    "proposed_status": proposed_status,
                    "possible_job_id": None,
                    "candidates": [],
                    "confidence": decision.confidence,
                    "review_required": True,
                    "reason": decision.reason,
                    "posted_at": message.posted_at.isoformat(),
                    "import_batch_id": self.import_batch_id,
                    "history_message_hash": history_hash,
                },
            )

    def mark_processing_error(self, line_message: dict[str, Any], error_type: str) -> None:
        if not self.client or not line_message.get("id"):
            return
        from apps.api.app.services.supabase import mark_line_message_processed

        mark_line_message_processed(self.client, line_message["id"], processing_error=error_type)


@dataclass(frozen=True)
class HistoryClassification:
    message_type: str
    confidence: float
    reason: str
    attachment_type: Optional[str] = None
    attachment_file_name: Optional[str] = None


def parse_history_text(text: str) -> list[HistoryMessage]:
    current_date: Optional[date] = None
    current_message: Optional[dict[str, Any]] = None
    messages: list[HistoryMessage] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        parsed_date = parse_history_date_line(line)
        if parsed_date:
            flush_message(messages, current_message)
            current_message = None
            current_date = parsed_date
            continue

        parsed_header = parse_message_header(line)
        if parsed_header and current_date:
            flush_message(messages, current_message)
            history_time, sender_name, first_text = parsed_header
            current_message = {
                "history_date": current_date,
                "history_time": history_time,
                "sender_name": sender_name,
                "lines": [first_text] if first_text else [],
            }
            continue

        if current_message is not None:
            current_message["lines"].append(line)

    flush_message(messages, current_message)
    return messages


def parse_history_date_line(line: str) -> Optional[date]:
    match = re.match(r"^\s*(\d{4})[./-](\d{1,2})[./-](\d{1,2})(?:\s+\S+)?\s*$", line)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def parse_message_header(line: str) -> Optional[tuple[time, str, str]]:
    match = re.match(r"^\s*(\d{1,2}):(\d{2})\s+(.+?)(?:\s+(.*))?$", line)
    if not match:
        return None
    sender_name = match.group(3).strip()
    first_text = (match.group(4) or "").strip()
    try:
        history_time = time(int(match.group(1)), int(match.group(2)))
    except ValueError:
        return None
    return history_time, sender_name, first_text


def flush_message(messages: list[HistoryMessage], current_message: Optional[dict[str, Any]]) -> None:
    if not current_message:
        return
    raw_text = "\n".join(current_message["lines"]).strip()
    if not raw_text:
        return
    messages.append(
        HistoryMessage(
            history_date=current_message["history_date"],
            history_time=current_message["history_time"],
            sender_name=current_message["sender_name"],
            raw_text=raw_text,
        )
    )


def classify_history_message(raw_text: str) -> HistoryClassification:
    compact = re.sub(r"\s+", "", raw_text)
    if is_non_job_announcement(raw_text):
        return HistoryClassification("attachment" if is_attachment_like_announcement(raw_text) else "announcement", 0.92, "History non-job announcement")
    if is_attachment_text(raw_text):
        return HistoryClassification("attachment", 0.95, "History attachment filename", attachment_type="file", attachment_file_name=raw_text.strip())
    if is_image_text(raw_text):
        return HistoryClassification("attachment", 0.9, "History image attachment", attachment_type="image", attachment_file_name=None)
    if is_member_event_text(compact):
        return HistoryClassification("member_event", 0.92, "History member event")
    if "新しいノートを作成しました" in compact or "アナウンスしました" in compact:
        return HistoryClassification("note_event", 0.9, "History note or announcement event")
    if "送信を取り消しました" in compact or "メッセージの送信を取り消しました" in compact:
        return HistoryClassification("unsend_event", 0.9, "History unsend event")
    if is_contact_note(raw_text):
        return HistoryClassification("contact_note", 0.82, "Phone/contact note")
    if re.search(r"(現状の残り台数|残り台数|^残り|残り\d+台|上がりました)", compact):
        return HistoryClassification("status_update", 0.82, "History remaining capacity update")
    if re.search(r"(配車完了しました|決まりました|無くなりました|自社で見つかったそうです|対応頂きました|対応いただきました|ありがとうございました)", compact):
        return HistoryClassification("job_closed", 0.86, "History close or assigned report")
    if re.search(r"(納品完了|配送完了|作業完了|配達完了|完了しました)", compact):
        return HistoryClassification("job_completed", 0.86, "History completion report")
    if is_work_job_text(compact):
        return HistoryClassification("work_job", 0.84, "History work job keyword")
    if is_driver_availability_text(compact):
        return HistoryClassification("vehicle_availability", 0.72, "History driver or vehicle availability")
    if re.search(r"(空車|空き車|空いてるドライバー|空いているドライバー|空いてる車両|空いている車両)", compact):
        return HistoryClassification("vehicle_availability", 0.84, "History vehicle availability keyword")
    if re.search(r"(軽幌車増車|増車いたしました)", compact) and not is_job_text(compact):
        return HistoryClassification("vehicle_availability", 0.72, "History vehicle increase notice")
    if re.search(r"(定期案件|定期便|毎週|365日|ルート配送)", compact) and is_job_text(compact):
        return HistoryClassification("regular_job", 0.82, "History regular job keyword")
    if is_job_text(compact):
        return HistoryClassification("job_request", 0.8, "History job keyword")
    base = classify_text(raw_text)
    if base.message_type == "irrelevant":
        return HistoryClassification("unknown", base.confidence, base.reason)
    return HistoryClassification(base.message_type, base.confidence, base.reason)


def is_attachment_text(raw_text: str) -> bool:
    text = raw_text.strip()
    return bool(re.match(r"^[^\n]+\.(?:pdf|docx?|xlsx?|png|jpe?g|gif|webp|zip)$", text, re.IGNORECASE))


def is_image_text(raw_text: str) -> bool:
    return raw_text.strip() in {"画像", "写真", "動画"} or bool(re.match(r"^(画像|写真|動画)\s*(を送信しました|)$", raw_text.strip()))


def is_attachment_like_announcement(raw_text: str) -> bool:
    return bool(re.search(r"(pdf|PDF|\.pdf|\.docx?|\.xlsx?)", raw_text))


def is_non_job_announcement(raw_text: str) -> bool:
    compact = re.sub(r"\s+", "", raw_text)
    return bool(
        re.search(r"(@All|懇親会|申込フォーム|Googleフォーム|docs\.google\.com/forms|forms\.gle|イベント案内|飲み会)", compact)
        or re.search(r"懇親会.*(?:PDF|pdf)", compact)
    )


def is_member_event_text(compact_text: str) -> bool:
    return any(
        phrase in compact_text
        for phrase in [
            "グループに参加しました",
            "グループを退会しました",
            "グループに招待しました",
            "グループから削除しました",
            "グループ招待",
            "招待致します",
            "招待します",
        ]
    ) or bool(re.search(r"(参加しました|招待しました|退会しました|削除しました|招待致します|招待します)$", compact_text))


def is_work_job_text(compact_text: str) -> bool:
    return bool(
        re.search(
            r"(搬入助手作業|搬出助手作業|荷下ろし作業|積込み作業案件|引越し助手|引越作業助手|引越し作業助手|駐禁対策要員|仕分け作業|倉庫作業|リフト作業|作業案件)",
            compact_text,
        )
    )


def is_driver_availability_text(compact_text: str) -> bool:
    return bool(
        re.search(r"(ドライバー情報|案件を探しております|案件を探しています|案件が有れば|案件があれば)", compact_text)
        and re.search(r"(軽貨物|軽バン|軽車両|車両|ドライバー|男性|女性)", compact_text)
    )


def is_job_text(compact_text: str) -> bool:
    return bool(
        re.search(
            r"(近距離配送|軽貨物案件|スポット案件|スポット便|チャーター|定期案件|着車|集荷|納品|引き取り|引取|下ろし|降ろし|配送|配達先|積み|荷主|運賃|走れる軽貨物|軽貨物を探しています|軽貨物さん居ませんか)",
            compact_text,
        )
    )


def is_contact_note(raw_text: str) -> bool:
    text = raw_text.strip()
    return bool(extract_phone_numbers(text)) and len(text) < 40 and not re.search(r"(集荷|納品|積み|下ろし|配送|案件)", text)


def extract_history_dates(raw_text: str, posted_date: date) -> dict[str, Any]:
    schedule_text = extract_schedule_text(raw_text)
    recurring = bool(re.search(r"(毎週|365日|週\d|土日祝のみ|月[〜~～\-ー]金|月[〜~～\-ー]水|月・火|月曜|火曜|水曜|木曜|金曜|土曜|日曜)", raw_text))
    ambiguous = bool(re.search(r"(下旬|上旬|中旬|初旬|頃|以降|決まり次第|応相談|相談可|毎週|365日|週\d|土日祝のみ)", raw_text))
    dates = explicit_dates(raw_text, posted_date)
    pickup_date = relative_date(raw_text, posted_date) or (dates[0] if dates else None)
    delivery_date = dates[1] if len(dates) > 1 else None
    if delivery_date is None and re.search(r"(下ろし|降ろし|納品|着)", raw_text) and dates:
        delivery_date = dates[-1]
    pickup_time = extract_time_near(raw_text, ["集荷", "積み", "着車"])
    delivery_time = extract_time_near(raw_text, ["納品", "下ろし", "降ろし", "終了"])
    return {
        "pickup_date": pickup_date.isoformat() if pickup_date else None,
        "delivery_date": delivery_date.isoformat() if delivery_date else None,
        "schedule_text": schedule_text,
        "pickup_time_text": pickup_time,
        "delivery_time_text": delivery_time,
        "date_confidence": 0.9 if pickup_date and not ambiguous else 0.45,
        "date_needs_review": not bool(pickup_date) or ambiguous,
        "recurring": recurring,
    }


def relative_date(raw_text: str, posted_date: date) -> Optional[date]:
    if re.search(r"本日|今日", raw_text):
        return posted_date
    if "明日" in raw_text:
        return posted_date + timedelta(days=1)
    if "明後日" in raw_text:
        return posted_date + timedelta(days=2)
    return None


def explicit_dates(raw_text: str, posted_date: date) -> list[date]:
    dates: list[date] = []
    for month, day in re.findall(r"(\d{1,2})[月/](\d{1,2})(?:日)?", raw_text):
        try:
            dates.append(date(posted_date.year, int(month), int(day)))
        except ValueError:
            continue
    return dates


def extract_schedule_text(raw_text: str) -> Optional[str]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    schedule_lines = [
        line
        for line in lines
        if re.search(r"(本日|今日|明日|明後日|\d{1,2}[月/]\d{1,2}|毎週|週\d|365日|土日祝|午前|午後|\d{1,2}:\d{2}|\d{1,2}時|下旬|上旬|中旬|初旬|以降|決まり次第|頃)", line)
    ]
    return " / ".join(schedule_lines[:3]) if schedule_lines else None


def extract_time_near(raw_text: str, keywords: list[str]) -> Optional[str]:
    for line in raw_text.splitlines():
        if any(keyword in line for keyword in keywords):
            match = re.search(r"(AM|PM|午前|午後)?\s*\d{1,2}(?::\d{2})?\s*(?:時|頃)?(?:[〜~～-]\s*\d{1,2}(?::\d{2})?\s*(?:時|頃)?)?", line, re.IGNORECASE)
            if match:
                return match.group(0).strip()
    return None


def history_common_fields(
    message: HistoryMessage,
    history_hash: str,
    import_batch_id: str,
    date_info: dict[str, Any],
) -> dict[str, Any]:
    return {
        "posted_at": message.posted_at.isoformat(),
        "pickup_date": date_info.get("pickup_date"),
        "scheduled_date": date_info.get("pickup_date"),
        "delivery_date": date_info.get("delivery_date"),
        "pickup_time_text": date_info.get("pickup_time_text"),
        "delivery_time_text": date_info.get("delivery_time_text"),
        "schedule_text": date_info.get("schedule_text"),
        "date_confidence": date_info.get("date_confidence"),
        "date_needs_review": date_info.get("date_needs_review"),
        "recurring": date_info.get("recurring"),
        "scheduled_time_text": date_info.get("pickup_time_text") or date_info.get("schedule_text"),
        "import_batch_id": import_batch_id,
        "history_message_hash": history_hash,
    }


def empty_date_info() -> dict[str, Any]:
    return {
        "pickup_date": None,
        "delivery_date": None,
        "schedule_text": None,
        "pickup_time_text": None,
        "delivery_time_text": None,
        "date_confidence": None,
        "date_needs_review": False,
        "recurring": False,
    }


def should_extract_dates(message_type: str) -> bool:
    return message_type in {"job_request", "regular_job", "work_job", "vehicle_availability"}


def proposed_status_for_history(message_type: str) -> tuple[str, str]:
    if message_type == "job_completed":
        return "completed_candidate", "completed"
    return "assigned_candidate", "assigned"


def history_message_hash(message: HistoryMessage) -> str:
    value = f"{message.history_date.isoformat()}|{message.history_time.isoformat(timespec='minutes')}|{message.sender_name}|{message.raw_text}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def first_phone(raw_text: str) -> Optional[str]:
    phones = extract_phone_numbers(raw_text)
    return phones[0] if phones else None


def increment_summary(summary: ImportSummary, message_type: str) -> None:
    if message_type in {"job_request", "regular_job", "work_job"}:
        summary.jobs += 1
    elif message_type == "vehicle_availability":
        summary.vehicle_availabilities += 1
    elif message_type in {"job_closed", "job_completed", "status_update", "availability_update"}:
        summary.status_updates += 1
    else:
        summary.ignored_events += 1


def print_dry_run_item(message: HistoryMessage, message_type: str, date_info: dict[str, Any]) -> None:
    print(
        json.dumps(
            {
                "posted_at": message.posted_at.isoformat(),
                "sender_name": message.sender_name,
                "message_type": message_type,
                "pickup_date": date_info.get("pickup_date"),
                "delivery_date": date_info.get("delivery_date"),
                "date_needs_review": date_info.get("date_needs_review"),
                "title_text": title_text(message.raw_text),
            },
            ensure_ascii=False,
        )
    )


def title_text(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    heading = next((line for line in lines if re.search(r"【[^】]+案件[^】]*】|【[^】]+】", line)), None)
    if heading:
        return heading[:80]
    job_name = next(
        (
            match.group(0)
            for match in [
                re.search(
                    r"(チャーター|スポット案件|スポット便|定期案件|搬入助手作業|搬出助手作業|荷下ろし作業|積込み作業案件|引越し助手|引越作業助手|引越し作業助手|近距離配送|軽貨物案件)",
                    raw_text,
                )
            ]
            if match
        ),
        None,
    )
    if job_name:
        return job_name
    meaningful_text = "\n".join(non_greeting_lines(lines))
    pickup, delivery = extract_route_locations(meaningful_text or raw_text)
    if pickup and delivery:
        return f"{pickup} → {delivery}"[:80]
    informative = next(iter(non_greeting_lines(lines)), None)
    return (informative or (lines[0] if lines else ""))[:80]


def non_greeting_lines(lines: list[str]) -> list[str]:
    return [
        line
        for line in lines
        if not re.fullmatch(r"(お世話になります。?|お疲れ様です。?|よろしくお願いします。?|いつもお世話になっております。?)", line)
    ]


def print_summary(summary: ImportSummary, *, import_batch_id: str, dry_run: bool) -> None:
    print("summary")
    print(f"dry_run: {str(dry_run).lower()}")
    print(f"import_batch_id: {import_batch_id}")
    print(f"messages: {summary.messages}")
    print(f"jobs: {summary.jobs}")
    print(f"vehicle_availabilities: {summary.vehicle_availabilities}")
    print(f"status_updates: {summary.status_updates}")
    print(f"ignored_events: {summary.ignored_events}")
    print(f"duplicates: {summary.duplicates}")
    print("message_type_counts:")
    for message_type, count in sorted((summary.message_type_counts or {}).items()):
        print(f"  {message_type}: {count}")
    unknown_samples = summary.unknown_samples or []
    if unknown_samples:
        print("unknown_samples:")
        for item in unknown_samples:
            print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Import failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
