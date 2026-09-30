# ─── Stage 1: build wheels (с тяжёлыми build-essential/libpq-dev) ────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
# Собираем колёса в отдельный каталог — затем копируем в финальный образ.
RUN pip wheel --wheel-dir=/wheels -r requirements.txt


# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# libpq нужна в рантайме для psycopg, curl — для healthcheck, tini — корректный PID 1.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpq5 \
      curl \
      tini \
 && rm -rf /var/lib/apt/lists/*

# Non-root юзер. uid фиксируем 10001, чтобы права на volume были предсказуемыми.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --create-home --shell /sbin/nologin app

WORKDIR /app

# Ставим зависимости из готовых колёс — без build tools в рантайме.
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# Копируем исходники и entrypoint.
COPY . .
RUN chmod +x /app/entrypoint.sh \
 && mkdir -p /app/uploads /app/.fastembed_cache \
 && chown -R app:app /app

# Предзагружаем модель эмбеддингов в образ на этапе сборки — контейнер стартует
# без сети (см. docs/tasks/038-semantic-auto-reply-matching.md, KB_EMBEDDING_CACHE_DIR).
USER app
RUN python -c "\
from app.core.config import settings; \
from fastembed import TextEmbedding; \
TextEmbedding(model_name=settings.KB_EMBEDDING_MODEL, cache_dir=settings.KB_EMBEDDING_CACHE_DIR)"

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
