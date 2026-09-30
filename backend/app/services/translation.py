from __future__ import annotations

from ..core.config import settings


def translate_to_en(text: str) -> str:
    if settings.TRANSLATION_PROVIDER == "noop":
        return text
    return text


def translate_values_to_en(values: dict) -> dict:
    """Применить перевод ко всем значениям заявки. Для checkbox/число — оригинал."""
    out: dict = {}
    for k, v in values.items():
        if isinstance(v, str):
            out[k] = translate_to_en(v)
        else:
            out[k] = v
    return out
