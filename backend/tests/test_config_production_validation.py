"""Settings._validate_production — Task 053 audit finding #3: a wildcard CORS_ORIGINS in
production, combined with main.py's CORSMiddleware(allow_credentials=True), reflects any
request's Origin back with credentials allowed. The validator must reject it at startup,
the same way it already rejects a weak JWT_SECRET or a missing BOT_INTERNAL_API_TOKEN.
"""

from __future__ import annotations

import pytest

from app.core.config import ConfigurationError, Settings, _validate_production


def _valid_production_settings(**overrides: object) -> Settings:
    fields = {
        "APP_ENV": "production",
        "JWT_SECRET": "a" * 40,
        "DEV_BYPASS_INITDATA": False,
        "BOT_INTERNAL_API_TOKEN": "b" * 32,
        "DATABASE_URL": "postgresql+psycopg://app:s3cr3t@db:5432/app",
        "CORS_ORIGINS": "https://admin.example.com,https://app.example.com",
        **overrides,
    }
    return Settings(**fields)


def test_valid_production_config_passes() -> None:
    _validate_production(_valid_production_settings())  # no raise


def test_wildcard_cors_origin_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="CORS_ORIGINS"):
        _validate_production(_valid_production_settings(CORS_ORIGINS="*"))


def test_wildcard_mixed_with_a_real_origin_is_still_rejected() -> None:
    with pytest.raises(ConfigurationError, match="CORS_ORIGINS"):
        _validate_production(
            _valid_production_settings(CORS_ORIGINS="https://admin.example.com,*")
        )


def test_non_wildcard_origin_list_still_passes() -> None:
    _validate_production(
        _valid_production_settings(CORS_ORIGINS="https://admin.example.com")
    )  # no raise — regression check that the new rule doesn't over-trigger
