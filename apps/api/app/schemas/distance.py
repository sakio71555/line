from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DistanceMeasureRequest(BaseModel):
    pickup_address: str = Field(min_length=1)
    delivery_address: str = Field(min_length=1)
    vehicle_type: Optional[str] = None
    posted_fare: Optional[str] = None

    @field_validator("pickup_address", "delivery_address", "vehicle_type", "posted_fare", mode="before")
    @classmethod
    def normalize_string(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

