"""Resize/convert arbitrary uploaded image bytes into a bounded WEBP thumbnail.

Pure technical utility -- no framework or domain imports, no knowledge of *why* a caller wants a
given size. Callers decide when to apply it and to which preset (see `presets.py`).
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError


class UnsupportedImageError(Exception):
    """The given bytes could not be decoded as an image."""


def optimize_image_bytes(content: bytes, *, max_width: int, max_height: int, quality: int = 100) -> bytes:
    """Resize to fit within (max_width, max_height) without upscaling, then encode as WEBP.

    Honors EXIF orientation (e.g. phone photos) before resizing.
    """
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise UnsupportedImageError(str(exc)) from exc

    image = ImageOps.exif_transpose(image)
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=quality, method=6)
    return buffer.getvalue()
