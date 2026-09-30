"""Общие фикстуры pytest. Для unit-тестов без БД."""

import os

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DEV_BYPASS_INITDATA", "false")
