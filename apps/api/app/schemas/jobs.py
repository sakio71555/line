from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RawLineJobCreate(BaseModel):
    source_group_id: str = Field(min_length=1)
    source_user_id: Optional[str] = None
    source_message_id: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)
