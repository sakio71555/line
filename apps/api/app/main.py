from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import get_settings
from .routers import (
    admin_jobs,
    admin_console,
    admin_line_messages,
    admin_status_updates,
    companies,
    distance,
    liff_forms,
    line_webhook,
    vehicle_availabilities,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LINE Transport Matching API",
    version="0.1.0",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://song-threats-knock-html.trycloudflare.com",
        settings.app_base_url,
    ],
    allow_origin_regex=r"https://.*\.trycloudflare\.com",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(line_webhook.router)
app.include_router(admin_console.router)
app.include_router(admin_jobs.router)
app.include_router(admin_line_messages.router)
app.include_router(admin_status_updates.router)
app.include_router(liff_forms.router)
app.include_router(companies.router)
app.include_router(vehicle_availabilities.router)
app.include_router(distance.router)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    fields = validation_error_fields(exc.errors())
    logger.warning("Request validation failed path=%s fields=%s", request.url.path, fields)
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "message": "入力データの形式が正しくありません",
                "fields": fields,
            }
        },
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def validation_error_fields(errors: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for error in errors:
        loc = error.get("loc")
        if not isinstance(loc, tuple) and not isinstance(loc, list):
            continue
        parts = [str(part) for part in loc if part != "body"]
        if not parts:
            continue
        field = ".".join(parts)
        if field not in fields:
            fields.append(field)
    return fields
