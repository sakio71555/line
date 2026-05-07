from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_env: str = Field(default="development", alias="API_ENV")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")

    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_secret_key: Optional[str] = Field(default=None, alias="SUPABASE_SECRET_KEY")
    supabase_service_role_key: Optional[str] = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    maps_api_key: Optional[str] = Field(default=None, alias="MAPS_API_KEY")

    line_channel_secret: str = Field(alias="LINE_CHANNEL_SECRET")
    line_channel_access_token: Optional[str] = Field(default=None, alias="LINE_CHANNEL_ACCESS_TOKEN")
    line_default_notify_group_id: Optional[str] = Field(default=None, alias="LINE_DEFAULT_NOTIFY_GROUP_ID")
    line_login_channel_id: Optional[str] = Field(default=None, alias="LINE_LOGIN_CHANNEL_ID")
    line_login_channel_secret: Optional[str] = Field(default=None, alias="LINE_LOGIN_CHANNEL_SECRET")
    liff_id: Optional[str] = Field(default=None, alias="LIFF_ID")
    liff_base_url: Optional[str] = Field(default=None, alias="LIFF_BASE_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def supabase_backend_key(self) -> str:
        key = self.supabase_secret_key or self.supabase_service_role_key
        if not key:
            raise ValueError("SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY is required")
        return key


@lru_cache
def get_settings() -> Settings:
    return Settings()
