from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobAnalysisResult(BaseModel):
    pickup_location: Optional[str] = None
    delivery_location: Optional[str] = None
    pickup_prefecture: Optional[str] = None
    delivery_prefecture: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time_text: Optional[str] = None
    delivery_date: Optional[str] = None
    vehicle_type: Optional[str] = None
    cargo_type: Optional[str] = None
    price: Optional[int] = None
    budget_note: Optional[str] = None
    notes: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    missing_fields: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("scheduled_date", "delivery_date")
    @classmethod
    def validate_scheduled_date(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        datetime.strptime(value, "%Y-%m-%d")
        return value
