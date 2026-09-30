import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import api_router
from .core.audit import AuditMiddleware
from .core.config import settings
from .core.errors import ApiError
from .core.http_headers import RequestIdMiddleware, SecurityHeadersMiddleware
from .core.logging import setup_logging
from .db.session import SessionLocal
from .modules.knowledge_base.application.use_cases import (
    backfill_faq_mirrors,
    backfill_missing_embeddings,
    warm_up_embedding_model,
)
from .modules.knowledge_base.infrastructure.embedding import FastEmbedEmbeddingPort
from .modules.knowledge_base.infrastructure.repositories import (
    SqlAlchemyKbDocumentRepository,
    SqlAlchemyKbFaqRepository,
)

log = logging.getLogger(__name__)


def _run_kb_embedding_backfill() -> None:
    if settings.APP_ROLE != "api":
        return
    embedder = FastEmbedEmbeddingPort()
    try:
        # Прогреваем модель безусловно — даже с пустой базой знаний (backfill ниже
        # тогда не находит документов и не трогает модель вовсе), чтобы первая
        # загрузка не выпала на первое реальное сообщение пользователя и не упёрлась
        # в HTTP-таймаут бот-адаптера.
        warm_up_embedding_model(embedder)
    except Exception:
        log.exception("KB embedding model warm-up failed — startup continues without it")
    db = SessionLocal()
    try:
        repository = SqlAlchemyKbDocumentRepository(db)
        updated = backfill_missing_embeddings(repository, embedder)
        if updated:
            db.commit()
            log.info("KB embedding backfill: %s document(s) updated", updated)
    except Exception:
        log.exception("KB embedding backfill failed — startup continues without it")
    finally:
        db.close()


def _run_faq_mirror_backfill() -> None:
    # Досоздаёт kb_documents-зеркала для FAQ, у которых их ещё нет (Task 052) —
    # тот же принцип "правки через /faq — единственный путь для новых/изменённых
    # записей, backfill закрывает существующие данные один раз при старте", что и
    # у _run_kb_embedding_backfill выше.
    if settings.APP_ROLE != "api":
        return
    db = SessionLocal()
    try:
        created = backfill_faq_mirrors(
            SqlAlchemyKbFaqRepository(db),
            SqlAlchemyKbDocumentRepository(db),
            FastEmbedEmbeddingPort(),
        )
        if created:
            db.commit()
            log.info("FAQ KB mirror backfill: %s document(s) created", created)
    except Exception:
        log.exception("FAQ KB mirror backfill failed — startup continues without it")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await asyncio.to_thread(_run_kb_embedding_backfill)
    await asyncio.to_thread(_run_faq_mirror_backfill)
    yield


app = FastAPI(
    title="RUT MULTI-BOT",
    version="0.1.0",
    description="Мульти-бот — backend (FastAPI).",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(RequestIdMiddleware)

if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.get("/healthz", tags=["health"])
def healthz() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}


app.include_router(api_router, prefix="/api")
