"""Named image-resize presets selectable via `POST /api/files`' optional `purpose` field."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImagePreset:
    max_width: int
    max_height: int
    quality: int = 100
    # Whether the `url` this upload's response carries should be a `ttl_seconds=-1` link. Only
    # true for presets whose image gets persisted into a DB column (category/draft/version
    # `image_url`) rather than re-signed fresh on every read from a stored bare attachment id --
    # that stored URL is exactly what the editor saves as-is, so if it's the default (30-day)
    # signature, the card image silently 404s as "link expired" a month after being set,
    # regardless of who's still referencing that attachment (see 20260925_1000's docstring,
    # which repairs exactly this for rows set before this field existed).
    permanent_url: bool = False


UPLOAD_IMAGE_PRESETS: dict[str, ImagePreset] = {
    # Category and capability-shortcut tile images -- rendered at 76x76 in the mini-app grid
    # (ContentCategoryGrid.tsx); Task 065. Persisted verbatim into image_url (see permanent_url).
    "category_icon": ImagePreset(max_width=128, max_height=128, quality=100, permanent_url=True),
}
