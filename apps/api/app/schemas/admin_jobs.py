from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


JobStatus = Literal[
    "needs_review",
    "open",
    "negotiating",
    "assigned",
    "in_progress",
    "completed",
    "cancelled",
    "hidden",
]
TaxType = Literal["税別", "税込", "不明"]


class AdminJobUpdate(BaseModel):
    pickup_location: Optional[str] = None
    delivery_location: Optional[str] = None
    pickup_prefecture: Optional[str] = None
    delivery_prefecture: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time_text: Optional[str] = None
    delivery_date: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_count: Optional[int] = Field(default=None, ge=1)
    cargo_type: Optional[str] = None
    price: Optional[int] = Field(default=None, ge=0)
    tax_type: Optional[TaxType] = None
    fee_note: Optional[str] = None
    highway_fee_note: Optional[str] = None
    budget_note: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone_numbers: Optional[list[str]] = None
    notes: Optional[str] = None
    status: Optional[JobStatus] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("scheduled_date", "delivery_date")
    @classmethod
    def validate_date(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator(
        "pickup_location",
        "delivery_location",
        "pickup_prefecture",
        "delivery_prefecture",
        "scheduled_time_text",
        "vehicle_type",
        "cargo_type",
        "tax_type",
        "fee_note",
        "highway_fee_note",
        "budget_note",
        "company_name",
        "contact_name",
        "notes",
        mode="before",
    )
    @classmethod
    def normalize_empty_string(cls, value: object) -> object:
        if value == "":
            return None
        return value


class AdminJobStatusUpdate(BaseModel):
    new_status: JobStatus
    reason: Optional[str] = None
    changed_by_line_user_id: Optional[str] = None
    changed_by_name: Optional[str] = "admin"

    model_config = ConfigDict(extra="forbid")


class StatusUpdateApply(BaseModel):
    job_id: Optional[str] = None
    new_status: Literal["assigned", "completed", "cancelled"] = "assigned"
    reason: Optional[str] = None
    changed_by_line_user_id: Optional[str] = None
    changed_by_name: Optional[str] = "admin"

    model_config = ConfigDict(extra="forbid")


class StatusUpdateIgnore(BaseModel):
    reviewed_by: Optional[str] = "admin"

    model_config = ConfigDict(extra="forbid")
