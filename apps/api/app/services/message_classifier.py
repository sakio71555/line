from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo


MessageType = str

PREFECTURES = [
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
]


VEHICLE_KEYWORDS = [
    "冷蔵軽貨物",
    "軽貨物",
    "軽バン",
    "軽冷蔵",
    "冷凍車",
    "冷蔵車",
    "10t",
    "10トン",
    "大型",
    "4t",
    "4トン",
    "2t",
    "2トン",
    "1t",
    "1トン",
    "ハイエース",
    "平車",
    "ウイング",
    "箱車",
]


@dataclass(frozen=True)
class ClassificationResult:
    message_type: MessageType
    confidence: float
    reason: str


def classify_line_event(event: dict[str, Any]) -> ClassificationResult:
    event_type = event.get("type")

    if event_type == "unsend":
        return ClassificationResult("unsend_event", 0.99, "LINE unsend event")

    if event_type in {"join", "leave", "memberJoined", "memberLeft", "follow", "unfollow"}:
        return ClassificationResult("member_event", 0.94, "LINE member/group event")

    if event_type != "message":
        return ClassificationResult("irrelevant", 0.6, f"Unsupported event type: {event_type}")

    message = event.get("message")
    if not isinstance(message, dict):
        return ClassificationResult("irrelevant", 0.6, "Message payload is missing")

    message_kind = message.get("type")
    if message_kind != "text":
        return ClassificationResult("attachment", 0.95, f"Non-text message: {message_kind}")

    text = message.get("text")
    return classify_text(text if isinstance(text, str) else "")


def classify_text(raw_text: str) -> ClassificationResult:
    text = normalize_text(raw_text)
    compact = re.sub(r"\s+", "", text)

    if not compact:
        return ClassificationResult("irrelevant", 0.7, "Empty text")

    if is_menu_request_text(compact):
        return ClassificationResult("menu_request", 0.98, "LIFF menu request keyword")

    if any(keyword in compact for keyword in ["送信を取り消しました", "メッセージの送信を取り消しました"]):
        return ClassificationResult("unsend_event", 0.9, "Unsend notice text")

    if "ノート" in compact and any(keyword in compact for keyword in ["作成", "投稿", "新しいノート"]):
        return ClassificationResult("note_event", 0.9, "LINE note notice")

    if any(keyword in compact for keyword in ["参加しました", "招待しました", "退出しました", "退会しました"]):
        return ClassificationResult("member_event", 0.86, "LINE member notice text")

    if _contains_any(compact, ["納品完了", "配送完了", "作業完了", "配達完了", "完了しました"]):
        return ClassificationResult("job_completed", 0.88, "Completion report keyword")

    if _contains_any(
        compact,
        ["決まりました", "対応頂きました", "対応いただきました", "埋まりました", "募集終了", "手配済", "決定しました"],
    ):
        return ClassificationResult("job_closed", 0.88, "Close or assigned report keyword")

    if _contains_any(compact, ["空車", "空き車", "車空き", "空いてます", "空いています"]):
        return ClassificationResult("vehicle_availability", 0.86, "Vehicle availability keyword")

    if _contains_any(compact, ["仕分け", "倉庫作業", "リフト作業", "作業案件"]):
        return ClassificationResult("work_job", 0.84, "Work job keyword")

    if _contains_any(compact, ["定期便", "定期案件", "継続案件", "ルート配送"]):
        return ClassificationResult("regular_job", 0.83, "Regular job keyword")

    if _contains_any(compact, ["スポット便", "チャーター", "積み", "下ろし", "降ろし", "卸し", "配送", "運賃"]):
        return ClassificationResult("job_request", 0.82, "Transport job keyword")

    if re.search(r"\d{1,2}/\d{1,2}|\d{1,2}月\d{1,2}日", compact) and _contains_any(
        compact,
        ["便", "積", "下", "卸", "車", "予算"],
    ):
        return ClassificationResult("job_request", 0.72, "Date and transport context")

    return ClassificationResult("irrelevant", 0.62, "No job-related keyword")


def build_line_job_payload(
    *,
    line_message: dict[str, Any],
    raw_text: str,
    message_type: str,
    confidence: float,
    line_user: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    reference_date = reference_date_from_line_message(line_message)
    payload = {
        "source_type": "line_group",
        "source_line_message_id": line_message.get("id"),
        "source_group_id": line_message.get("source_group_id"),
        "source_user_id": line_message.get("source_user_id"),
        "source_message_id": line_message.get("source_message_id"),
        "created_by_line_user_id": line_message.get("source_user_id"),
        "raw_text": raw_text,
        "pickup_location": None,
        "delivery_location": None,
        "pickup_prefecture": None,
        "delivery_prefecture": None,
        "scheduled_date": None,
        "scheduled_time_text": extract_time_text(raw_text),
        "delivery_date": None,
        "vehicle_type": extract_vehicle_type(raw_text),
        "vehicle_count": extract_vehicle_count(raw_text),
        "cargo_type": extract_cargo_hint(raw_text),
        "price": extract_price(raw_text),
        "tax_type": extract_tax_type(raw_text),
        "fee_note": extract_fee_note(raw_text),
        "highway_fee_note": extract_highway_fee_note(raw_text),
        "budget_note": extract_budget_note(raw_text),
        "phone_numbers": extract_phone_numbers(raw_text),
        "status": "needs_review",
        "analysis_status": "pending",
        "review_required": True,
        "confidence": confidence,
        "missing_fields": build_missing_fields(raw_text),
        "job_category": job_category_from_message_type(message_type, raw_text),
        "notes": raw_text if message_type in {"regular_job", "work_job"} else None,
    }
    payload = postprocess_job_fields(raw_text, payload, reference_date=reference_date)
    return enrich_line_job_contact_fields(payload, line_user=line_user)


def build_vehicle_availability_payload(
    *,
    line_message: dict[str, Any],
    raw_text: str,
    confidence: float,
) -> dict[str, Any]:
    prefecture = extract_first_prefecture(raw_text)
    return {
        "source_line_message_id": line_message.get("id"),
        "source_group_id": line_message.get("source_group_id"),
        "source_user_id": line_message.get("source_user_id"),
        "location": extract_first_location(raw_text),
        "prefecture": prefecture,
        "vehicle_type": extract_vehicle_type(raw_text),
        "available_from": None,
        "company_name": None,
        "contact_name": None,
        "phone_numbers": extract_phone_numbers(raw_text),
        "status": "open",
        "review_required": True,
        "confidence": confidence,
        "raw_text": raw_text,
    }


def job_category_from_message_type(message_type: str, raw_text: str) -> str:
    compact = re.sub(r"\s+", "", raw_text)
    if message_type == "regular_job":
        return "regular"
    if message_type == "work_job":
        return "work"
    if "チャーター" in compact:
        return "charter"
    if "スポット" in compact:
        return "spot"
    return "other"


def proposed_status_from_message_type(message_type: str) -> tuple[str, str]:
    if message_type == "job_completed":
        return "completed_candidate", "completed"
    return "job_closed", "assigned"


def event_received_at(event: dict[str, Any]) -> Optional[str]:
    timestamp = event.get("timestamp")
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).isoformat()
    return None


def reference_date_from_line_message(line_message: dict[str, Any]) -> date:
    received_at = line_message.get("received_at")
    if isinstance(received_at, str):
        parsed = parse_datetime(received_at)
        if parsed:
            return parsed.astimezone(ZoneInfo("Asia/Tokyo")).date()
    return date.today()


def normalize_text(raw_text: str) -> str:
    return raw_text.replace("\u3000", " ").strip()


def is_menu_request_text(compact_text: str) -> bool:
    return compact_text in {"メニュー", "案件投稿", "空車登録", "案件一覧", "フォーム", "企業検索"}


def extract_source_group_id(source: dict[str, Any]) -> Optional[str]:
    if source.get("type") == "group" and isinstance(source.get("groupId"), str):
        return source["groupId"]
    if source.get("type") == "room" and isinstance(source.get("roomId"), str):
        return source["roomId"]
    if source.get("type") == "user" and isinstance(source.get("userId"), str):
        return source["userId"]
    return None


def extract_message_info(event: dict[str, Any]) -> dict[str, Optional[str]]:
    message = event.get("message")
    unsend = event.get("unsend")
    source_message_id = None
    raw_text = None
    attachment_type = None
    attachment_file_name = None
    attachment_message_id = None

    if isinstance(message, dict):
        message_type = message.get("type")
        message_id = message.get("id")
        source_message_id = message_id if isinstance(message_id, str) else None
        if message_type == "text" and isinstance(message.get("text"), str):
            raw_text = message["text"]
        elif isinstance(message_type, str):
            attachment_type = message_type
            attachment_message_id = source_message_id
            file_name = message.get("fileName") or message.get("file_name")
            attachment_file_name = file_name if isinstance(file_name, str) else None

    if isinstance(unsend, dict):
        target_message_id = unsend.get("messageId")
        source_message_id = target_message_id if isinstance(target_message_id, str) else source_message_id

    return {
        "source_message_id": source_message_id,
        "raw_text": raw_text,
        "attachment_type": attachment_type,
        "attachment_file_name": attachment_file_name,
        "attachment_message_id": attachment_message_id,
    }


def extract_first_prefecture(text: str) -> Optional[str]:
    return extract_prefecture_from_location(text)


def extract_route_prefectures(text: str) -> tuple[Optional[str], Optional[str]]:
    pickup_location, delivery_location = extract_route_locations(text)
    return (
        extract_prefecture_from_location(pickup_location or ""),
        extract_prefecture_from_location(delivery_location or ""),
    )


def extract_first_location(text: str) -> Optional[str]:
    cleaned = clean_route_segment(text)
    match = re.search(r"([一-龥ぁ-んァ-ヶA-Za-z0-9]+(?:都|道|府|県)[一-龥ぁ-んァ-ヶA-Za-z0-9]*(?:市|区|町|村))", cleaned)
    if match:
        return match.group(1)
    match = re.search(r"([一-龥ぁ-んァ-ヶA-Za-z0-9]+(?:市|区|町|村))", cleaned)
    return match.group(1) if match else extract_first_prefecture(cleaned)


def extract_route_locations(text: str) -> tuple[Optional[str], Optional[str]]:
    route = extract_route_parts(text)
    if route:
        pickup_segment, delivery_segment = route
        return clean_route_segment(pickup_segment), clean_route_segment(delivery_segment)

    arrow_parts = re.split(r"→|->|から|〜|～", text, maxsplit=1)
    if len(arrow_parts) == 2:
        return extract_first_location(arrow_parts[0]), extract_first_location(arrow_parts[1])
    locations = re.findall(r"([一-龥ぁ-んァ-ヶA-Za-z0-9]+(?:市|区|町|村))", text)
    if len(locations) >= 2:
        return locations[0], locations[1]
    return (locations[0], None) if locations else (None, None)


def extract_vehicle_type(text: str) -> Optional[str]:
    compact = re.sub(r"\s+", "", text)
    for keyword in VEHICLE_KEYWORDS:
        if keyword in compact:
            return keyword
    return None


def extract_vehicle_count(text: str) -> Optional[int]:
    match = re.search(r"(\d+)\s*(?:台|車)", text)
    return int(match.group(1)) if match else None


def extract_first_date(text: str) -> Optional[str]:
    matches = _extract_dates(text)
    return matches[0] if matches else None


def extract_second_date(text: str) -> Optional[str]:
    matches = _extract_dates(text)
    return matches[1] if len(matches) > 1 else None


def _extract_dates(text: str, reference_date: Optional[date] = None) -> list[str]:
    base_date = reference_date or date.today()
    found: list[str] = []
    for month, day in re.findall(r"(\d{1,2})[月/](\d{1,2})(?:日)?", text):
        try:
            parsed = date(base_date.year, int(month), int(day))
            if parsed < base_date - timedelta(days=180):
                parsed = date(base_date.year + 1, int(month), int(day))
            found.append(parsed.isoformat())
        except ValueError:
            continue
    return found


def extract_time_text(text: str) -> Optional[str]:
    match = re.search(
        r"((?:午前|午後)\s*\d{1,2}(?::\d{2})?\s*(?:時|頃)?|\d{1,2}:\d{2}|\d{1,2}\s*時(?:\s*[~-]\s*\d{1,2}\s*時)?)",
        text,
    )
    if match:
        return match.group(1).strip()
    return None


def extract_cargo_hint(text: str) -> Optional[str]:
    for keyword in ["冷凍食品", "食品", "雑貨", "家具", "建材", "書類", "アスクル"]:
        if keyword in text:
            return keyword
    return None


def extract_price(text: str) -> Optional[int]:
    oku = re.search(r"(\d+(?:\.\d+)?)\s*万", text)
    if oku:
        return int(float(oku.group(1)) * 10000)
    yen = re.search(r"([0-9,]+)\s*円", text)
    if yen:
        return int(yen.group(1).replace(",", ""))
    return None


def extract_tax_type(text: str) -> Optional[str]:
    if "税別" in text:
        return "税別"
    if "税込" in text:
        return "税込"
    return None


def extract_fee_note(text: str) -> Optional[str]:
    match = re.search(r"([0-9.]+%\s*(?:あり|有|手数料)|手数料\s*[^\s、。]*)", text)
    return match.group(1) if match else None


def extract_highway_fee_note(text: str) -> Optional[str]:
    match = re.search(r"(高速代[^\s、。]*|片道高速[^\s、。]*)", text)
    return match.group(1) if match else None


def extract_budget_note(text: str) -> Optional[str]:
    for keyword in ["低予算", "帰り車希望", "相談可", "応相談"]:
        if keyword in text:
            return keyword
    return None


def extract_phone_numbers(text: str) -> list[str]:
    return re.findall(r"0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}", text)


def enrich_line_job_contact_fields(
    payload: dict[str, Any],
    *,
    line_user: Optional[dict[str, Any]],
) -> dict[str, Any]:
    enriched = dict(payload)
    raw_text = str(enriched.get("raw_text") or "")
    phone_numbers = extract_phone_numbers(raw_text)
    line_user = line_user or {}
    display_name = line_user.get("display_name")

    enriched["created_by_display_name"] = display_name or enriched.get("created_by_display_name")
    enriched["contact_line_user_id"] = enriched.get("source_user_id")
    enriched["contact_display_name"] = display_name or enriched.get("contact_display_name")
    enriched["company_name"] = enriched.get("company_name") or line_user.get("company_name")
    enriched["contact_name"] = enriched.get("contact_name") or line_user.get("contact_name")

    registered_phone = line_user.get("phone_number")
    if phone_numbers:
        enriched["contact_phone"] = phone_numbers[0]
        enriched["contact_method"] = "phone"
        enriched["contact_missing"] = False
    elif isinstance(registered_phone, str) and registered_phone:
        enriched["contact_phone"] = registered_phone
        enriched["contact_method"] = "registered_phone"
        enriched["contact_missing"] = False
    else:
        enriched["contact_phone"] = None
        enriched["contact_method"] = "group_reply_or_admin"
        enriched["contact_missing"] = True
        enriched["review_required"] = True

    return enriched


def build_missing_fields(text: str, fields: Optional[dict[str, Any]] = None) -> list[str]:
    fields = fields or {}
    missing: list[str] = []
    checks = {
        "pickup_location": fields.get("pickup_location") or extract_route_locations(text)[0],
        "delivery_location": fields.get("delivery_location") or extract_route_locations(text)[1],
        "scheduled_date": fields.get("scheduled_date") or extract_first_date(text),
        "vehicle_type": fields.get("vehicle_type") or extract_vehicle_type(text),
        "price": fields.get("price") if "price" in fields else extract_price(text),
    }
    for field, value in checks.items():
        if value is None:
            missing.append(field)
    return missing


def postprocess_job_fields(
    raw_text: str,
    fields: dict[str, Any],
    *,
    reference_date: Optional[date] = None,
) -> dict[str, Any]:
    reference = reference_date or date.today()
    payload = dict(fields)
    route = extract_route_parts(raw_text)

    if route:
        pickup_segment, delivery_segment = route
        pickup_location = clean_route_segment(pickup_segment)
        delivery_location = clean_route_segment(delivery_segment)
        payload["pickup_location"] = pickup_location or payload.get("pickup_location")
        payload["delivery_location"] = delivery_location or payload.get("delivery_location")

        scheduled_date = extract_scheduled_date(raw_text, pickup_segment, reference)
        delivery_date = extract_delivery_date(delivery_segment, reference)
        if scheduled_date:
            payload["scheduled_date"] = scheduled_date
        if delivery_date:
            payload["delivery_date"] = delivery_date
    else:
        pickup_location, delivery_location = extract_route_locations(raw_text)
        payload["pickup_location"] = pickup_location or payload.get("pickup_location")
        payload["delivery_location"] = delivery_location or payload.get("delivery_location")
        if not payload.get("scheduled_date"):
            payload["scheduled_date"] = extract_scheduled_date(raw_text, raw_text, reference)
        if not payload.get("delivery_date"):
            dates = _extract_dates(raw_text, reference)
            if len(dates) >= 2:
                payload["delivery_date"] = dates[1]

    if payload.get("pickup_location"):
        payload["pickup_location"] = clean_route_segment(str(payload["pickup_location"]))
        payload["pickup_prefecture"] = extract_prefecture_from_location(payload["pickup_location"])
    if payload.get("delivery_location"):
        payload["delivery_location"] = clean_route_segment(str(payload["delivery_location"]))
        payload["delivery_prefecture"] = extract_prefecture_from_location(payload["delivery_location"])

    payload["vehicle_type"] = payload.get("vehicle_type") or extract_vehicle_type(raw_text)
    rule_budget_note = extract_budget_note(raw_text)
    payload["budget_note"] = rule_budget_note or payload.get("budget_note")
    payload["price"] = extract_price(raw_text)
    existing_missing = set(payload.get("missing_fields") or [])
    refreshed_missing = set(build_missing_fields(raw_text, payload))
    for filled_field in {
        "pickup_location",
        "delivery_location",
        "scheduled_date",
        "vehicle_type",
        "price",
    }:
        if payload.get(filled_field) is not None:
            existing_missing.discard(filled_field)
    payload["missing_fields"] = sorted(existing_missing | refreshed_missing)
    return payload


def extract_route_parts(text: str) -> Optional[tuple[str, str]]:
    normalized = normalize_text(text)
    pattern = re.compile(
        r"(?P<pickup>[\s\S]{1,80}?)(?:積み|発|集荷)\s*(?:→|->|から|〜|～)\s*(?P<delivery>[\s\S]{1,80}?)(?:下ろし|降ろし|卸し|納品|着)",
        re.MULTILINE,
    )
    match = pattern.search(normalized)
    if match:
        return match.group("pickup"), match.group("delivery")
    return None


def clean_route_segment(segment: str) -> str:
    cleaned = normalize_text(segment)
    cleaned = remove_date_expressions(cleaned)
    cleaned = re.sub(r"(積み|発|集荷|下ろし|降ろし|卸し|納品|着)$", "", cleaned)
    cleaned = re.sub(r"^[、,\s]+|[、,\s]+$", "", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


def remove_date_expressions(text: str) -> str:
    cleaned = re.sub(r"(本日|今日|明日|明後日)", "", text)
    cleaned = re.sub(r"\d{1,2}\s*[月/]\s*\d{1,2}\s*(?:日)?(?:\([月火水木金土日]\))?", "", cleaned)
    cleaned = re.sub(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "", cleaned)
    return cleaned


def extract_scheduled_date(raw_text: str, pickup_segment: str, reference_date: date) -> Optional[str]:
    if re.search(r"本日|今日", raw_text):
        return reference_date.isoformat()
    if "明日" in raw_text:
        return (reference_date + timedelta(days=1)).isoformat()
    if "明後日" in raw_text:
        return (reference_date + timedelta(days=2)).isoformat()
    dates = _extract_dates(pickup_segment, reference_date)
    return dates[0] if dates else None


def extract_delivery_date(delivery_segment: str, reference_date: date) -> Optional[str]:
    dates = _extract_dates(delivery_segment, reference_date)
    return dates[0] if dates else None


def extract_prefecture_from_location(location: str) -> Optional[str]:
    matches: list[tuple[int, str]] = []
    for prefecture in PREFECTURES:
        index = location.find(prefecture)
        if index >= 0:
            matches.append((index, prefecture))
    if not matches:
        return None
    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def parse_datetime(value: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
