from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from ..core.config import get_settings
from ..services.llm_parser import JobAnalysisError, analyze_raw_text
from ..services.supabase import (
    fetch_job_by_id,
    fetch_next_unanalyzed_job,
    get_supabase_client,
    mark_job_analysis_failed,
    update_job_analysis,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze transport job raw_text with OpenAI.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--raw-text", help="Analyze the given raw_text without saving to Supabase.")
    group.add_argument("--next-unparsed", action="store_true", help="Analyze one pending job from Supabase.")
    group.add_argument("--job-id", help="Analyze and update a specific job by id.")
    args = parser.parse_args()

    settings = get_settings()

    if args.raw_text is not None:
        return analyze_text_only(args.raw_text, settings)

    try:
        client = get_supabase_client()
        if args.next_unparsed:
            job = fetch_next_unanalyzed_job(client)
            if job is None:
                print(json.dumps({"ok": True, "message": "No pending jobs found"}, ensure_ascii=False))
                return 0
        else:
            job = fetch_job_by_id(client, args.job_id)
            if job is None:
                print(json.dumps({"ok": False, "error": "Job not found"}, ensure_ascii=False))
                return 1
    except Exception as exc:
        print_safe_error("Supabase request failed", exc)
        return 1

    return analyze_and_save_job(job, settings, client)


def analyze_text_only(raw_text: str, settings) -> int:
    try:
        analysis = analyze_raw_text(raw_text, settings)
    except JobAnalysisError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(analysis.model_dump_json(indent=2))
    return 0


def analyze_and_save_job(job: dict, settings, client) -> int:
    job_id = job["id"]
    try:
        analysis = analyze_raw_text(job["raw_text"], settings)
        updated = update_job_analysis(client, job_id, analysis, settings.openai_model)
    except JobAnalysisError as exc:
        try:
            mark_job_analysis_failed(client, job_id, str(exc), settings.openai_model)
        except Exception:
            pass
        print(json.dumps({"ok": False, "job_id": job_id, "error": str(exc)}, ensure_ascii=False))
        return 1
    except Exception as exc:
        print_safe_error("Job analysis save failed", exc, {"job_id": job_id})
        return 1

    output = {
        "ok": True,
        "job_id": job_id,
        "analysis_status": updated.get("analysis_status"),
        "review_required": updated.get("review_required"),
        "confidence": updated.get("confidence"),
        "missing_fields": updated.get("missing_fields"),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def print_safe_error(message: str, exc: Exception, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {
        "ok": False,
        "error": message,
        "error_type": exc.__class__.__name__,
    }
    if extra:
        payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
