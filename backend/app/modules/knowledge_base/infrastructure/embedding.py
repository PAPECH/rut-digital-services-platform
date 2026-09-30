from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from ....core.config import settings

if TYPE_CHECKING:
    from fastembed import TextEmbedding

log = logging.getLogger(__name__)


class _ModelState:
    """Мутируемый контейнер вместо module-level global — один на процесс."""

    def __init__(self) -> None:
        self.model: TextEmbedding | None = None
        self.load_failed = False


# Модуль-уровневый singleton: модель грузится один раз на процесс, а не на каждый
# новый экземпляр FastEmbedEmbeddingPort — presentation-слой конструирует порт
# per-request (как и репозитории), но кеш модели должен это пережить.
_model_lock = threading.Lock()
_state = _ModelState()


def _get_model() -> "TextEmbedding | None":
    """Ленивая загрузка модели эмбеддингов — один раз на процесс."""
    if _state.model is not None or _state.load_failed:
        return _state.model
    with _model_lock:
        if _state.model is not None or _state.load_failed:
            return _state.model
        try:
            from fastembed import TextEmbedding

            supported = {m["model"] for m in TextEmbedding.list_supported_models()}
            if settings.KB_EMBEDDING_MODEL not in supported:
                log.error(
                    "KB_EMBEDDING_MODEL=%s не поддерживается fastembed — семантический "
                    "матчинг отключён",
                    settings.KB_EMBEDDING_MODEL,
                )
                _state.load_failed = True
                return None
            _state.model = TextEmbedding(
                model_name=settings.KB_EMBEDDING_MODEL,
                cache_dir=settings.KB_EMBEDDING_CACHE_DIR,
            )
        except Exception:
            log.exception("Не удалось загрузить модель эмбеддингов — семантический матчинг отключён")
            _state.load_failed = True
    return _state.model


class FastEmbedEmbeddingPort:
    """Реализация application.ports.EmbeddingPort поверх fastembed/ONNX — CPU-only,
    без сети в рантайме (модель предзагружается в образ, см. backend/Dockerfile).
    Экземпляр этого класса дёшево создавать per-request (как SqlAlchemy-репозитории)
    — сама модель кешируется на уровне модуля, не на уровне экземпляра."""

    def embed(self, text: str) -> list[float] | None:
        """Синхронный, CPU-bound вызов. Из async-кода звать только через to_thread."""
        model = _get_model()
        if model is None:
            return None
        text = text.strip()
        if not text:
            return None
        try:
            vector = next(iter(model.embed([text])))
        except Exception:
            log.exception("Сбой при вычислении эмбеддинга")
            return None
        return vector.tolist()

    def warm_up(self) -> None:
        _get_model()
