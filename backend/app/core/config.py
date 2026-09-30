from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_LOG_LEVEL: str = "INFO"
    APP_ROLE: Literal["api", "worker"] = "api"

    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"
    JWT_EXPIRES_MIN: int = 60 * 24 * 30
    ADMIN_ACCESS_EXPIRES_MIN: int = 15
    ADMIN_REFRESH_EXPIRES_DAYS: int = 30
    ADMIN_SESSION_ABSOLUTE_DAYS: int = 90
    ADMIN_REFRESH_COOKIE_NAME: str = "platform_admin_refresh"
    ADMIN_CSRF_COOKIE_NAME: str = "platform_admin_csrf"

    CORS_ORIGINS: str = ""

    DATABASE_URL: str = "postgresql+psycopg://mfc:mfc@db:5432/mfc"
    REDIS_URL: str = "redis://redis:6379/0"

    # MAX
    MAX_BOT_TOKEN: str = ""
    BEAVERS_BOT_TOKEN: str = ""
    MAX_BOT_USERNAME: str = ""

    PUBLIC_API_URL: str = "http://localhost:8000"
    PUBLIC_MINIAPP_URL: str = "http://localhost:5174"
    PUBLIC_ADMIN_URL: str = "http://localhost:5173"

    # Экземпляр платформы по умолчанию, если клиент не передал X-Bot-Slug.
    DEFAULT_BOT_SLUG: str = "default"

    TRANSLATION_PROVIDER: Literal["noop"] = "noop"
    AI_PROVIDER: Literal["kb_semantic", "off"] = "kb_semantic"
    # ONNX-квантованная модель через fastembed — CPU-only, без сети в рантайме.
    # Меняя модель, свериться с fastembed's TextEmbedding.list_supported_models()
    # и синхронизировать размерность с KbDocumentRecord.embedding
    # (modules/knowledge_base/infrastructure/models.py) + миграцией.
    KB_EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # Модель предзагружается в этот путь на этапе сборки образа (см. backend/Dockerfile),
    # чтобы старт контейнера не требовал сети.
    KB_EMBEDDING_CACHE_DIR: str = "/app/.fastembed_cache"
    KB_MAX_CANDIDATES: int = 3
    # Cosine similarity = 1 - cosine_distance. Откалибровано эмпирически на реальном
    # прогоне (fastembed + pgvector, 2 синтетических RU-документа): близкие перефразы
    # ложатся в ~0.74-0.75, размытые-но-связанные запросы — в ~0.58-0.61, случайные —
    # в ~0.48-0.52 (см. docs/tasks/038-semantic-auto-reply-matching.md). На реальном
    # контенте ботов имеет смысл сверить и подправить при необходимости.
    KB_AUTO_ANSWER_THRESHOLD: float = 0.70
    KB_CANDIDATE_MIN_THRESHOLD: float = 0.55
    # Автоответ допустим только при заметном отрыве лучшего документа от второго.
    # При близких результатах пользователю безопаснее предложить варианты (Task 089).
    KB_AUTO_ANSWER_MIN_MARGIN: float = 0.05

    GOOGLE_SHEETS_MODE: Literal["mock", "live"] = "mock"
    GOOGLE_SHEETS_MOCK_FILE: str = "/app/seed/google_sheets_mock.json"
    GOOGLE_SHEETS_ID: str = ""
    GOOGLE_SHEETS_RANGE: str = "B:C"
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = ""
    MONITORING_INTERVAL_SECONDS: int = 300
    ADMISSION_MONITORING_INTERVAL_SECONDS: int = 1800

    # rut_schedule capability's data source -- "miit_web" scrapes the university's public
    # timetable site (temporary; only reachable from the nightly worker, never live per-request,
    # see modules/capabilities/rut_schedule/infrastructure/sync_worker.py); "oracle" reads the
    # same hierarchy/lessons from an Oracle DB instead once that access exists. Flip this literal
    # value yourself once Oracle credentials below are filled in -- there is no admin-UI toggle.
    RUT_SCHEDULE_PROVIDER: Literal["miit_web", "oracle"] = "miit_web"
    RUT_SCHEDULE_ORACLE_DSN: str = ""
    RUT_SCHEDULE_ORACLE_USER: str = ""
    RUT_SCHEDULE_ORACLE_PASSWORD: str = ""

    BOT_MODE: Literal["mock", "live"] = "mock"
    BOT_INTERNAL_API_URL: str = "http://backend:8000"
    BOT_INTERNAL_API_TOKEN: str = ""
    BOT_MANAGED_ENV_FILE: str = "/app/secrets/bots.env"

    DEV_BYPASS_INITDATA: bool = False

    UPLOADS_DIR: str = "/app/uploads"

    # Task 064 -- consent gate. PRIVACY_POLICY_URL is linked from the consent prompt in both
    # the bot and the mini-app; POLICY_VERSION is stamped on every given/revoked event so a
    # future change to the policy text doesn't retroactively relabel past consent.
    PRIVACY_POLICY_URL: str = (
        "https://rut-miit.ru/content/"
        "Положение%20о%20работе%20с%20персональными%20данными.pdf?id_wm=986949"
    )
    POLICY_VERSION: str = "2024-05-02"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


_WEAK_SECRET_MARKERS = ("change-me", "example", "secret", "todo", "please")
_WEAK_INTERNAL_TOKEN_DEFAULT = "internal-bot-token-change-me"


class ConfigurationError(RuntimeError):
    """Стартовая ошибка конфигурации — несовместимая для прода настройка."""


def _validate_production(settings: "Settings") -> None:
    errors: list[str] = []

    s = (settings.JWT_SECRET or "").strip()
    if len(s) < 32:
        errors.append("JWT_SECRET слишком короткий (нужно ≥32 символа случайных байт).")
    if any(m in s.lower() for m in _WEAK_SECRET_MARKERS):
        errors.append("JWT_SECRET содержит маркер дефолтного значения — выпустить новый.")

    if settings.DEV_BYPASS_INITDATA:
        errors.append("DEV_BYPASS_INITDATA=true запрещён в production (обход MAX-подписи).")

    internal = (settings.BOT_INTERNAL_API_TOKEN or "").strip()
    if not internal:
        errors.append("BOT_INTERNAL_API_TOKEN пуст — бот сможет писать ingress без аутентификации.")
    elif internal == _WEAK_INTERNAL_TOKEN_DEFAULT or len(internal) < 16:
        errors.append("BOT_INTERNAL_API_TOKEN слишком слабый или равен дефолту.")

    pg = settings.DATABASE_URL or ""

    if ":mfc@" in pg or ":postgres@" in pg or ":password@" in pg:
        errors.append("DATABASE_URL содержит дефолтный пароль — заменить.")

    if not settings.cors_origins_list:
        errors.append("CORS_ORIGINS пуст в production (фронт не сможет ходить в API).")
    elif any("localhost" in o or "127.0.0.1" in o for o in settings.cors_origins_list):
        errors.append("CORS_ORIGINS содержит localhost — выпилить для production.")
    elif "*" in settings.cors_origins_list:
        # allow_credentials=True (main.py) + a wildcard origin makes CORSMiddleware reflect
        # any request's Origin back with credentials allowed — the classic reflected-origin
        # credential-leak misconfiguration (Task 053 audit finding #3).
        errors.append(
            "CORS_ORIGINS содержит '*' — вместе с allow_credentials=True это позволяет "
            "любому origin делать credentialed-запросы к API. Перечислить явные origin."
        )

    if errors:
        msg = "Production configuration is unsafe:\n  - " + "\n  - ".join(errors)
        raise ConfigurationError(msg)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.is_production:
        _validate_production(s)
    return s


settings = get_settings()
