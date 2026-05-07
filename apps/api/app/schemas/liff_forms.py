from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


JobCategory = Literal["spot", "charter", "regular", "work", "other"]
TaxType = Literal["税別", "税込", "不明"]


class LiffJobCreate(BaseModel):
    job_category: JobCategory
    pickup_prefecture: str = Field(min_length=1)
    pickup_city: str = Field(min_length=1)
    pickup_address: Optional[str] = None
    delivery_prefecture: str = Field(min_length=1)
    delivery_city: str = Field(min_length=1)
    delivery_address: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time_text: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_time_text: Optional[str] = None
    vehicle_type: str = Field(min_length=1)
    vehicle_count: int = Field(default=1, ge=1)
    cargo_type: Optional[str] = None
    price: Optional[int] = Field(default=None, ge=0)
    tax_type: TaxType = "不明"
    highway_fee_note: Optional[str] = None
    fee_note: Optional[str] = None
    notes: Optional[str] = None
    distance_km: Optional[float] = Field(default=None, ge=0)
    distance_text: Optional[str] = None
    distance_source: Optional[str] = None
    standard_fare_yen: Optional[int] = Field(default=None, ge=0)
    fare_ratio_percent: Optional[float] = Field(default=None, ge=0)
    fare_judgement: Optional[str] = None
    fare_calc_status: Optional[str] = "not_calculated"
    fare_calc_note: Optional[str] = None
    fare_region: Optional[str] = None
    fare_vehicle_class: Optional[str] = None
    fare_vehicle_label: Optional[str] = None
    company_name: str = Field(min_length=1)
    contact_name: str = Field(min_length=1)
    phone_number: str = Field(min_length=1)
    line_user_id: Optional[str] = None
    display_name: Optional[str] = None
    session_id: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("scheduled_date", "delivery_date")
    @classmethod
    def validate_date(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("company_name", "contact_name", "phone_number", mode="before")
    @classmethod
    def normalize_required_string(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "pickup_address",
        "delivery_address",
        "scheduled_time_text",
        "delivery_time_text",
        "cargo_type",
        "highway_fee_note",
        "fee_note",
        "notes",
        "distance_text",
        "distance_source",
        "fare_judgement",
        "fare_calc_status",
        "fare_calc_note",
        "fare_region",
        "fare_vehicle_class",
        "fare_vehicle_label",
        "line_user_id",
        "display_name",
        "session_id",
        mode="before",
    )
    @classmethod
    def normalize_empty_string(cls, value: object) -> object:
        if value == "":
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class LiffVehicleAvailabilityCreate(BaseModel):
    prefecture: str = Field(min_length=1)
    city: str = Field(min_length=1)
    vehicle_type: str = Field(min_length=1)
    available_from: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone_number: Optional[str] = None
    notes: Optional[str] = None
    line_user_id: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("available_from")
    @classmethod
    def validate_available_from(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @field_validator(
        "available_from",
        "company_name",
        "contact_name",
        "phone_number",
        "notes",
        "line_user_id",
        mode="before",
    )
    @classmethod
    def normalize_empty_string(cls, value: object) -> object:
        if value == "":
            return None
        return value
