from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from ..core.config import Settings, get_settings
from ..core.security import verify_line_signature
from ..services.line_push import LinePushError, push_help_message, push_menu_message
from ..services.line_reply import reply_help_message, reply_menu_message
from ..services.line_profile import fetch_line_profile
from ..services.message_classifier import (
    build_line_job_payload,
    build_vehicle_availability_payload,
    classify_line_event,
    event_received_at,
    extract_message_info,
    extract_source_group_id,
    proposed_status_from_message_type,
)
from ..services.supabase import (
    create_liff_session,
    create_job_from_line_message,
    create_status_update_from_line_message,
    create_vehicle_availability,
    get_supabase_client,
    mark_line_message_processed,
    mark_unsent_message,
    save_line_message,
    upsert_line_user,
)

router = APIRouter(prefix="/line", tags=["line"])


@router.post("/webhook")
async def receive_line_webhook(
    request: Request,
    x_line_signature: Optional[str] = Header(default=None, alias="X-Line-Signature"),
    settings: Settings = Depends(get_settings),
) -> dict[str, Union[int, bool]]:
    body = await request.body()

    if not verify_line_signature(body, x_line_signature, settings.line_channel_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid LINE signature",
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from exc

    events = payload.get("events", [])
    if not isinstance(events, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="events must be a list",
        )

    try:
        supabase = get_supabase_client()
        saved_count = 0
        processed_count = 0
        skipped_count = 0
        error_count = 0

        for event in events:
            if not isinstance(event, dict):
                skipped_count += 1
                continue

            classification = classify_line_event(event)
            line_message_payload = build_line_message_payload(event, classification)
            line_message = save_line_message(supabase, line_message_payload)
            line_user = resolve_line_user(supabase, line_message, settings)
            saved_count += 1

            try:
                did_process = process_classified_message(
                    supabase=supabase,
                    line_message=line_message,
                    line_user=line_user,
                    message_type=classification.message_type,
                    settings=settings,
                    reply_token=event.get("replyToken") if isinstance(event.get("replyToken"), str) else None,
                )
                if did_process:
                    processed_count += 1
                mark_line_message_processed(supabase, line_message["id"])
            except Exception as exc:
                error_count += 1
                mark_line_message_processed(
                    supabase,
                    line_message["id"],
                    processing_error=exc.__class__.__name__,
                )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to save LINE message",
        ) from exc

    return {
        "ok": True,
        "received": len(events),
        "saved": saved_count,
        "processed": processed_count,
        "skipped": skipped_count,
        "errors": error_count,
    }


def build_line_message_payload(event: dict[str, Any], classification) -> dict[str, Any]:
    source = event.get("source") if isinstance(event.get("source"), dict) else {}
    source = source if isinstance(source, dict) else {}
    message_info = extract_message_info(event)
    return {
        "source_group_id": extract_source_group_id(source),
        "source_user_id": source.get("userId") if isinstance(source.get("userId"), str) else None,
        "source_message_id": message_info["source_message_id"],
        "event_type": event.get("type") if isinstance(event.get("type"), str) else None,
        "message_type": classification.message_type,
        "raw_text": message_info["raw_text"],
        "attachment_type": message_info["attachment_type"],
        "attachment_file_name": message_info["attachment_file_name"],
        "attachment_message_id": message_info["attachment_message_id"],
        "is_unsent": classification.message_type == "unsend_event",
        "received_at": event_received_at(event),
        "classification_confidence": classification.confidence,
        "classification_reason": classification.reason,
    }


def process_classified_message(
    *,
    supabase,
    line_message: dict[str, Any],
    line_user: Optional[dict[str, Any]],
    message_type: str,
    settings: Settings,
    reply_token: Optional[str],
) -> bool:
    raw_text = line_message.get("raw_text")
    if not isinstance(raw_text, str):
        raw_text = ""

    if message_type == "menu_request":
        handle_menu_request(
            supabase=supabase,
            line_message=line_message,
            settings=settings,
            reply_token=reply_token,
        )
        return True

    if message_type == "help_request":
        handle_help_request(
            supabase=supabase,
            line_message=line_message,
            settings=settings,
            reply_token=reply_token,
        )
        return True

    if message_type in {"job_request", "regular_job", "work_job"}:
        create_job_from_line_message(
            supabase,
            build_line_job_payload(
                line_message=line_message,
                raw_text=raw_text,
                message_type=message_type,
                confidence=float(line_message.get("classification_confidence") or 0.0),
                line_user=line_user,
            ),
        )
        return True

    if message_type == "vehicle_availability":
        create_vehicle_availability(
            supabase,
            build_vehicle_availability_payload(
                line_message=line_message,
                raw_text=raw_text,
                confidence=float(line_message.get("classification_confidence") or 0.0),
            ),
        )
        return True

    if message_type in {"job_closed", "job_completed"}:
        update_type, proposed_status = proposed_status_from_message_type(message_type)
        create_status_update_from_line_message(
            supabase,
            line_message=line_message,
            raw_text=raw_text,
            update_type=update_type,
            proposed_status=proposed_status,
            confidence=float(line_message.get("classification_confidence") or 0.0),
            reason=line_message.get("classification_reason") or message_type,
            line_user=line_user,
        )
        return True

    if message_type == "unsend_event":
        source_message_id = line_message.get("source_message_id")
        if isinstance(source_message_id, str):
            mark_unsent_message(supabase, source_message_id)
        return True

    return False


def handle_menu_request(
    *,
    supabase,
    line_message: dict[str, Any],
    settings: Settings,
    reply_token: Optional[str],
) -> None:
    source_group_id = line_message.get("source_group_id")
    source_user_id = line_message.get("source_user_id")
    if is_group_or_room_source(source_group_id):
        session = create_liff_session(supabase, line_message)
        try:
            push_menu_message(
                settings,
                source_user_id if isinstance(source_user_id, str) else None,
                session_id=session.get("session_id") if isinstance(session.get("session_id"), str) else None,
            )
        except LinePushError as exc:
            mark_line_message_processed(
                supabase,
                line_message["id"],
                processing_error=exc.__class__.__name__,
            )
        return

    reply_menu_message(settings, reply_token, session_id=None)


def handle_help_request(
    *,
    supabase,
    line_message: dict[str, Any],
    settings: Settings,
    reply_token: Optional[str],
) -> None:
    source_group_id = line_message.get("source_group_id")
    source_user_id = line_message.get("source_user_id")
    if is_group_or_room_source(source_group_id):
        try:
            push_help_message(
                settings,
                source_user_id if isinstance(source_user_id, str) else None,
            )
        except LinePushError as exc:
            mark_line_message_processed(
                supabase,
                line_message["id"],
                processing_error=exc.__class__.__name__,
            )
        return

    reply_help_message(settings, reply_token)


def is_group_or_room_source(value: object) -> bool:
    return isinstance(value, str) and value.startswith(("C", "R"))


def resolve_line_user(supabase, line_message: dict[str, Any], settings: Settings) -> Optional[dict[str, Any]]:
    source_user_id = line_message.get("source_user_id")
    if not isinstance(source_user_id, str) or not source_user_id:
        return None

    profile = fetch_line_profile(
        settings=settings,
        source_group_id=line_message.get("source_group_id")
        if isinstance(line_message.get("source_group_id"), str)
        else None,
        source_user_id=source_user_id,
    )
    try:
        return upsert_line_user(
            supabase,
            line_user_id=source_user_id,
            display_name=(profile or {}).get("display_name"),
            picture_url=(profile or {}).get("picture_url"),
        )
    except Exception:
        return None


def build_raw_job_from_event(event: object):  # Backward-compatible helper for older tests.
    if not isinstance(event, dict):
        return None

    if event.get("type") != "message":
        return None

    message = event.get("message")
    if not isinstance(message, dict) or message.get("type") != "text":
        return None

    source = event.get("source")
    if not isinstance(source, dict):
        return None

    source_group_id = get_source_group_id(source)
    source_message_id = message.get("id")
    raw_text = message.get("text")

    if not source_group_id or not source_message_id or not raw_text:
        return None

    source_user_id = source.get("userId")

    from ..schemas.jobs import RawLineJobCreate

    return RawLineJobCreate(
        source_group_id=source_group_id,
        source_user_id=source_user_id if isinstance(source_user_id, str) else None,
        source_message_id=source_message_id,
        raw_text=raw_text,
    )


def get_source_group_id(source: dict[str, Any]) -> Optional[str]:
    source_type = source.get("type")

    if source_type == "group":
        group_id = source.get("groupId")
        return group_id if isinstance(group_id, str) else None

    if source_type == "room":
        room_id = source.get("roomId")
        return room_id if isinstance(room_id, str) else None

    return None
