import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from os import getenv


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PUBLIC_WEBAPP_URL: str = getenv("PUBLIC_WEBAPP_URL", "http://localhost:5174")
    PUBLIC_WEBHOOK_BASE_URL: str = getenv(
        "PUBLIC_WEBHOOK_BASE_URL", getenv("PUBLIC_WEBAPP_URL", "http://localhost:8080")
    )

    MAX_BOT_TOKEN: str = getenv("MAX_BOT_TOKEN", "")
    BOT_TOKEN_ENV_KEY: str = getenv("BOT_TOKEN_ENV_KEY", "MAX_BOT_TOKEN")
    MAX_BOT_USERNAME: str = getenv("MAX_BOT_USERNAME", "rut_mfc_test_bot")
    BOT_SLUG: str = getenv("BOT_SLUG", getenv("DEFAULT_BOT_SLUG", "default"))

    PUBLIC_MINIAPP_URL: str = "http://localhost:5174"
    PUBLIC_API_URL: str = "http://localhost:8000"

    BOT_MODE: Literal["mock", "live"] = "live"
    BOT_INTERNAL_API_URL: str = "http://backend:8000"
    BOT_INTERNAL_API_TOKEN: str = ""
    BOT_MANAGED_ENV_FILE: str = "/app/secrets/bots.env"
    BOT_RUNTIME_TOKEN: str = ""
    BOT_RUNTIME_VERSION: str = "dev"
    BOT_HEARTBEAT_SECONDS: int = 60
    BOT_SUPERVISOR_INTERVAL_SECONDS: int = 10
    BOT_WEBHOOK_SECRET: str = ""
    BOT_WEBHOOK_URL: str = ""
    BOT_WEBHOOK_HOST: str = "127.0.0.1"
    BOT_WEBHOOK_PORT: int = 18080
    BOT_WEBHOOK_GATEWAY_HOST: str = "0.0.0.0"
    BOT_WEBHOOK_GATEWAY_PORT: int = 8080
    BOT_WEBHOOK_CHILD_PORT_BASE: int = 18080
    BOT_WEBHOOK_CHILD_PORT_LIMIT: int = 512

    REDIS_URL: str = "redis://redis:6379/0"
    APP_LOG_LEVEL: str = "INFO"
    USE_WEBHOOK: bool = getenv("USE_WEBHOOK", "false").lower() == "true"

    # Task 064 -- same default as backend/app/core/config.py's PRIVACY_POLICY_URL, and both
    # read the same .env, so this only diverges if .env overrides one but not the other.
    # Used strictly as a fallback when the backend consent-status/accept call itself fails
    # (network hiccup, stale runtime token, etc.) -- the backend's own policy_url is always
    # preferred when that call succeeds. Without this, a failed backend call previously
    # produced a consent prompt with an empty link instead of a working one.
    PRIVACY_POLICY_URL: str = (
        "https://rut-miit.ru/content/"
        "Положение%20о%20работе%20с%20персональными%20данными.pdf?id_wm=986949"
    )

    @property
    def max_bot_token(self) -> str:
        return os.getenv(self.BOT_TOKEN_ENV_KEY, "") or self.MAX_BOT_TOKEN



settings = Settings()
