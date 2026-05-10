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
    "closed",
    "deleted",
    "hidden",
]
JobCategory = Literal["spot", "charter", "regular", "work", "driver_recruitment", "referral_request", "other"]
PostingType = Literal["delivery", "other"]
TaxType = Literal["税別", "税込", "不明"]


class AdminJobUpdate(BaseModel):
    posting_type: Optional[PostingType] = None
    job_category: Optional[JobCategory] = None
    title: Optional[str] = None
    free_text: Optional[str] = None
    target_area: Optional[str] = None
    pickup_location: Optional[str] = None
    delivery_location: Optional[str] = None
    pickup_prefecture: Optional[str] = None
    pickup_city: Optional[str] = None
    pickup_address: Optional[str] = None
    delivery_prefecture: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_address: Optional[str] = None
    pickup_date: Optional[str] = None
    pickup_time_text: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time_text: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_time_text: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_count: Optional[int] = Field(default=None, ge=1)
    cargo_type: Optional[str] = None
    price: Optional[int] = Field(default=None, ge=0)
    posted_fare_yen: Optional[int] = Field(default=None, ge=0)
    distance_km: Optional[float] = Field(default=None, ge=0)
    distance_text: Optional[str] = None
    distance_source: Optional[str] = None
    standard_fare_yen: Optional[int] = Field(default=None, ge=0)
    fare_ratio_percent: Optional[float] = Field(default=None, ge=0)
    fare_ratio_text: Optional[str] = None
    fare_judgement: Optional[str] = None
    fare_calc_status: Optional[str] = None
    fare_calc_note: Optional[str] = None
    fare_region: Optional[str] = None
    fare_vehicle_class: Optional[str] = None
    fare_vehicle_label: Optional[str] = None
    tax_type: Optional[TaxType] = None
    fee_note: Optional[str] = None
    highway_fee_note: Optional[str] = None
    budget_note: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone_number: Optional[str] = None
    phone_numbers: Optional[list[str]] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("pickup_date", "scheduled_date", "delivery_date")
    @classmethod
    def validate_date(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator(
        "pickup_location",
        "delivery_location",
        "posting_type",
        "title",
        "free_text",
        "target_area",
        "pickup_prefecture",
        "pickup_city",
        "pickup_address",
        "delivery_prefecture",
        "delivery_city",
        "delivery_address",
        "pickup_time_text",
        "scheduled_time_text",
        "delivery_time_text",
        "vehicle_type",
        "cargo_type",
        "tax_type",
        "fee_note",
        "highway_fee_note",
        "budget_note",
        "company_name",
        "contact_name",
        "phone_number",
        "notes",
        "distance_text",
        "distance_source",
        "fare_judgement",
        "fare_ratio_text",
        "fare_calc_status",
        "fare_calc_note",
        "fare_region",
        "fare_vehicle_class",
        "fare_vehicle_label",
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
