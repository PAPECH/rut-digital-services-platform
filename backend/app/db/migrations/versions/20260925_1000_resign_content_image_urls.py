"""Re-sign and un-expire `content_categories`/`content_drafts`/`content_versions`.image_url.

Two independent bugs on the same columns, both fixed here since both need the same
select-and-rewrite pass:

1. Task 053 moved file-URL signing from a raw HMAC over JWT_SECRET to a purpose-derived subkey
   (`HmacPurpose.FILE_URL`, see `app.core.security`). Every other `make_signed_url()` call site
   recomputes its URL fresh on every read (e.g. `content.presentation.router._attachment_urls`,
   `news.presentation.router._response`); these three columns are the one place a signed URL gets
   persisted verbatim instead, so every one signed before that scheme change now fails
   `verify_signed()` as `bad_signature` no matter what its `exp` says.

2. Independent of (1): the admin editor (`ContentDraftEditor.tsx`) sets a card image straight from
   the generic upload endpoint's response (`attachment.url`), which is signed with
   `make_signed_url()`'s *default* 30-day TTL, not `ttl_seconds=-1` -- so a persisted card image
   silently 404s as `link_expired` 30 days after being set, regardless of the HMAC scheme, and
   regardless of whether it was ever re-signed by fix (1). `content.presentation.router`'s own
   `_attachment_urls` docstring is explicit that a card image "must never expire" -- that's the
   only design intent on record for this field, so every row this touches gets pinned to
   `exp=-1` here rather than kept at whatever TTL it happened to carry. (The editor still needs
   its own follow-up fix so newly-set images don't drift back into this same trap in 30 days --
   out of scope for a data migration.)

Also normalizes a third, unrelated pre-existing shape found on the same columns while writing
this: some rows carry `/api/files/{id}/{urlencoded original name}?exp=...` instead of the plain
`/api/files/{id}?exp=...` shape `make_signed_url()` actually produces -- `api/routes/files.py`
only ever registered a single `GET /{file_id}` route, never one with a trailing name segment, so
those never resolved (404 before signature verification even ran), independent of both bugs
above. There's nothing to gain by keeping that shape -- `download()` already sends the real
filename via `Content-Disposition` from `Attachment.original_name`, not from the URL -- so this
drops the name segment down to the one shape the app actually serves, rather than adding a second
route to keep matching it.

Safe to run more than once: re-deriving the same (file_id, exp=-1) signature twice yields an
identical row, so a repeat run is a no-op.

HKDF/HMAC logic duplicated from `app.core.security` rather than imported -- migrations in this
repo don't reach into application code (see 20260821_1438_content_attachment_references.py's
`_card_image_attachment_id`), so this keeps working unchanged if that module's shape ever moves.

Revision ID: 796ed462577d
Revises: 9a1f3e7c5b02
Create Date: 2026-09-25 10:00:00
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "796ed462577d"
down_revision: str | None = "9a1f3e7c5b02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# file_id, then an optional /<name> segment `make_signed_url()` never produces (see module
# docstring) that gets dropped, then the real query string -- `exp` itself is discarded (always
# rewritten to -1, see module docstring point 2), `sig` is replaced, and anything after it (e.g.
# `&action=view`) is preserved verbatim.
_SIGNED_URL_RE = re.compile(r"^/api/files/(\d+)(?:/[^?]*)?\?exp=(-?\d+)&sig=[0-9a-f]+(.*)$")

_PERMANENT_EXP = "-1"

_TABLES = ("content_categories", "content_drafts", "content_versions")


def _hkdf_sha256(ikm: bytes, info: bytes, length: int = 32) -> bytes:
    prk = hmac.new(b"\x00" * hashlib.sha256().digest_size, ikm, hashlib.sha256).digest()
    okm = b""
    previous = b""
    counter = 1
    while len(okm) < length:
        previous = hmac.new(prk, previous + info + bytes([counter]), hashlib.sha256).digest()
        okm += previous
        counter += 1
    return okm[:length]


def _file_url_signature(file_id: str, exp: str) -> str:
    jwt_secret = os.environ.get("JWT_SECRET", "change-me")
    subkey = _hkdf_sha256(jwt_secret.encode("utf-8"), b"file_url")
    return hmac.new(subkey, f"{file_id}.{exp}".encode("utf-8"), hashlib.sha256).hexdigest()


def upgrade() -> None:
    bind = op.get_bind()
    for table in _TABLES:
        rows = bind.execute(
            sa.text(f"SELECT id, image_url FROM {table} WHERE image_url IS NOT NULL")
        ).mappings().all()
        for row in rows:
            match = _SIGNED_URL_RE.match(row["image_url"])
            if match is None:
                continue
            file_id, suffix = match.group(1), match.group(3)
            sig = _file_url_signature(file_id, _PERMANENT_EXP)
            new_url = f"/api/files/{file_id}?exp={_PERMANENT_EXP}&sig={sig}{suffix}"
            if new_url == row["image_url"]:
                continue
            bind.execute(
                sa.text(f"UPDATE {table} SET image_url = :url WHERE id = :id"),
                {"url": new_url, "id": row["id"]},
            )


def downgrade() -> None:
    # No-op: the pre-migration signature isn't recoverable (it depended on whatever scheme was
    # live before Task 053), and re-computing it under the same current scheme has nothing to
    # undo -- this migration only ever repairs a signature mismatch or an unservable URL shape,
    # it doesn't change what the data means.
    pass
