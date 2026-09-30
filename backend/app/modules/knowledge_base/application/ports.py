from __future__ import annotations

from typing import Protocol


class EmbeddingPort(Protocol):
    def embed(self, text: str) -> list[float] | None:
        """Синхронный, CPU-bound вызов. Из async-кода звать только через to_thread."""
        ...

    def warm_up(self) -> None:
        """Форсирует загрузку модели в память (см. application.use_cases.warm_up_embedding_model)."""
        ...
