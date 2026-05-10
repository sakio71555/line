from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DistanceMeasureRequest(BaseModel):
    pickup_address: str = Field(min_length=1)
    delivery_address: str = Field(min_length=1)
    pickup_prefecture: Optional[str] = None
    vehicle_type: Optional[str] = None
    posted_fare: Optional[str] = None
    price: Optional[str] = None
    fare: Optional[str] = None
    pickup_detail_missing: bool = False
    delivery_detail_missing: bool = False

    @field_validator("pickup_address", "delivery_address", "pickup_prefecture", "vehicle_type", "posted_fare", "price", "fare", mode="before")
    @classmethod
    def normalize_string(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    def effective_posted_fare(self) -> Optional[str]:
        return self.posted_fare or self.price or self.fare
