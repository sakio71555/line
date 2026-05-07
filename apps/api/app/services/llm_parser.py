from __future__ import annotations

import json
from datetime import date
from json import JSONDecodeError
from typing import Any

import httpx
from pydantic import ValidationError

from ..core.config import Settings
from ..schemas.job_analysis import JobAnalysisResult
from .message_classifier import postprocess_job_fields


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
REVIEW_REQUIRED_CONFIDENCE_THRESHOLD = 0.7

ANALYSIS_FIELD_NAMES = [
    "pickup_location",
    "delivery_location",
    "pickup_prefecture",
    "delivery_prefecture",
    "scheduled_date",
    "scheduled_time_text",
    "delivery_date",
    "vehicle_type",
    "cargo_type",
    "price",
    "budget_note",
    "notes",
]

REQUIRED_ANALYSIS_FIELD_NAMES = [
    "pickup_location",
    "delivery_location",
    "pickup_prefecture",
    "delivery_prefecture",
    "scheduled_date",
    "scheduled_time_text",
    "vehicle_type",
    "cargo_type",
    "price",
    "notes",
]

JOB_ANALYSIS_JSON_SCHEMA: dict[str, Any] = {
    "name": "transport_job_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "pickup_location": {"type": ["string", "null"]},
            "delivery_location": {"type": ["string", "null"]},
            "pickup_prefecture": {"type": ["string", "null"]},
            "delivery_prefecture": {"type": ["string", "null"]},
            "scheduled_date": {
                "type": ["string", "null"],
                "description": "Date in YYYY-MM-DD format when inferable, otherwise null.",
            },
            "scheduled_time_text": {"type": ["string", "null"]},
            "delivery_date": {
                "type": ["string", "null"],
                "description": "Delivery date in YYYY-MM-DD format when inferable, otherwise null.",
            },
            "vehicle_type": {"type": ["string", "null"]},
            "cargo_type": {"type": ["string", "null"]},
            "price": {
                "type": ["integer", "null"],
                "description": "Freight price as an integer JPY amount when inferable, otherwise null.",
            },
            "budget_note": {
                "type": ["string", "null"],
                "description": "Budget constraints such as 低予算, 帰り車希望, 相談可, otherwise null.",
            },
            "notes": {"type": ["string", "null"]},
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Overall extraction confidence from 0 to 1.",
            },
            "missing_fields": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ANALYSIS_FIELD_NAMES,
                },
                "description": "Fields that could not be confidently extracted.",
            },
        },
        "required": [
            "pickup_location",
            "delivery_location",
            "pickup_prefecture",
            "delivery_prefecture",
            "scheduled_date",
            "scheduled_time_text",
            "delivery_date",
            "vehicle_type",
            "cargo_type",
            "price",
            "budget_note",
            "notes",
            "confidence",
            "missing_fields",
        ],
    },
}


class JobAnalysisError(Exception):
    pass


def analyze_raw_text(raw_text: str, settings: Settings) -> JobAnalysisResult:
    if not settings.openai_api_key:
        raise JobAnalysisError("OPENAI_API_KEY is not configured")

    current_date = date.today().isoformat()

    try:
        response = httpx.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You extract structured Japanese transport job data. "
                            "Return only JSON that matches the provided schema. "
                            "Use null for unknown values. Use missing_fields for any value "
                            "that is unknown or not confidently supported by the text. "
                            "Do not guess prefectures unless the location clearly implies one. "
                            "For route expressions like 'A積み→B下ろし', always treat A as pickup "
                            "and B as delivery. Treat 'A積み', 'A発', 'A集荷' as pickup markers; "
                            "treat 'B下ろし', 'B降ろし', 'B納品', 'B着' as delivery markers. "
                            "Remove date expressions such as '5月2日' from location fields. "
                            "If the text says '本日' or '今日', scheduled_date is the current date. "
                            "If a delivery segment like '5月2日埼玉県日高市下ろし' appears, set "
                            "delivery_date to that date and delivery_location to the location only. "
                            "Extract prefectures from the final pickup/delivery location strings. "
                            f"Current date is {current_date}. If the text has a month/day "
                            "without a year, infer the nearest future date based on the current date. "
                            "If a date still cannot be safely inferred, use null."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"案件投稿本文:\n{raw_text}",
                    },
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": JOB_ANALYSIS_JSON_SCHEMA,
                },
            },
            timeout=60,
        )
    except httpx.HTTPError as exc:
        raise JobAnalysisError(f"OpenAI API request failed: {exc.__class__.__name__}") from exc

    if response.status_code >= 400:
        raise JobAnalysisError(f"OpenAI API request failed with status {response.status_code}")

    try:
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, JSONDecodeError) as exc:
        raise JobAnalysisError("OpenAI API response did not contain JSON content") from exc

    try:
        decoded = json.loads(content)
    except JSONDecodeError as exc:
        raise JobAnalysisError("OpenAI API response content was not valid JSON") from exc

    try:
        result = JobAnalysisResult.model_validate(decoded)
    except ValidationError as exc:
        raise JobAnalysisError("OpenAI API response JSON did not match the expected schema") from exc

    postprocessed = postprocess_job_fields(
        raw_text,
        result.model_dump(),
        reference_date=date.today(),
    )
    return normalize_missing_fields(JobAnalysisResult.model_validate(postprocessed))


def normalize_missing_fields(result: JobAnalysisResult) -> JobAnalysisResult:
    missing_fields = set(result.missing_fields)

    for field_name in REQUIRED_ANALYSIS_FIELD_NAMES:
        value = getattr(result, field_name)
        if value is None or value == "":
            missing_fields.add(field_name)

    normalized = result.model_copy(
        update={"missing_fields": sorted(missing_fields)}
    )
    return normalized


def is_review_required(result: JobAnalysisResult) -> bool:
    return result.confidence < REVIEW_REQUIRED_CONFIDENCE_THRESHOLD or bool(result.missing_fields)
