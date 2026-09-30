"""Unit tests for `app.shared.images.optimize_image_bytes` (Task 065). Pure Pillow logic, no
FastAPI/DB involved -- HTTP-level wiring (the `purpose` field on `POST /api/files`) is covered by
`test_files_upload_http.py`."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.shared.images import UnsupportedImageError, optimize_image_bytes


def _png_bytes(width: int, height: int, mode: str = "RGB") -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, (width, height), color=0).save(buffer, "PNG")
    return buffer.getvalue()


def test_resizes_landscape_to_fit_within_bounds():
    result = optimize_image_bytes(_png_bytes(500, 300), max_width=128, max_height=128)
    with Image.open(io.BytesIO(result)) as image:
        assert image.width == 128
        assert image.height == 77  # aspect ratio preserved


def test_resizes_portrait_to_fit_within_bounds():
    result = optimize_image_bytes(_png_bytes(300, 500), max_width=128, max_height=128)
    with Image.open(io.BytesIO(result)) as image:
        assert image.height == 128
        assert image.width == 77


def test_never_upscales_smaller_source():
    result = optimize_image_bytes(_png_bytes(40, 20), max_width=128, max_height=128)
    with Image.open(io.BytesIO(result)) as image:
        assert (image.width, image.height) == (40, 20)


def test_honors_exif_orientation():
    buffer = io.BytesIO()
    image = Image.new("RGB", (200, 100), color=(10, 20, 30))
    exif = image.getexif()
    exif[0x0112] = 6  # Orientation: rotate 90 CW
    image.save(buffer, "JPEG", exif=exif)

    result = optimize_image_bytes(buffer.getvalue(), max_width=128, max_height=128)

    with Image.open(io.BytesIO(result)) as rotated:
        # Orientation 6 swaps width/height once applied.
        assert rotated.width < rotated.height


def test_converts_non_rgb_mode_to_savable_webp():
    result = optimize_image_bytes(_png_bytes(64, 64, mode="P"), max_width=128, max_height=128)
    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "WEBP"
        assert image.mode in ("RGB", "RGBA")


def test_output_is_valid_webp():
    result = optimize_image_bytes(_png_bytes(200, 200), max_width=128, max_height=128)
    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "WEBP"


def test_rejects_undecodable_bytes():
    with pytest.raises(UnsupportedImageError):
        optimize_image_bytes(b"not an image", max_width=128, max_height=128)
