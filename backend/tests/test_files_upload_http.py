"""Integration tests for `POST /api/files`, in particular the optional `purpose` field added by
Task 065 (category/shortcut tile image resize-to-WEBP). Follows the real-Postgres-session pattern
`test_users_admin_http.py` established for routes that commit ORM rows directly."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import app.main  # noqa: F401 -- registers every ORM class in Base.metadata.
from app.api.deps import CurrentPrincipal, get_current_principal
from app.api.routes.files import router
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.attachment import Attachment
from app.models.enums import AdminRoleEnum
from app.modules.admins.infrastructure.models import Admin
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.bot_instances.infrastructure.models import BotInstanceRecord
from app.modules.tenancy.presentation.dependencies import require_tenant_access


def _png_bytes(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=(200, 50, 50)).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOADS_DIR", str(tmp_path))

    db = SessionLocal()
    suffix = uuid4().hex[:10]
    bot = BotInstanceRecord(slug=f"test-files-{suffix}", name="Test Files Bot")
    admin = Admin(
        max_user_id=f"admin-{suffix}", full_name="Test Admin", role=AdminRoleEnum.admin, is_active=True
    )
    db.add_all([bot, admin])
    db.commit()
    db.refresh(bot)
    db.refresh(admin)

    app = FastAPI()
    app.include_router(router, prefix="/files")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_tenant_access] = lambda: BotInstance(
        id=bot.id, slug=bot.slug, name=bot.name
    )
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        sub=f"a:{admin.id}", role="admin", system="max", user_id=None, admin_id=admin.id
    )

    client = TestClient(app)
    try:
        yield client, db
    finally:
        db.rollback()
        db.delete(bot)  # cascades attachments
        db.commit()
        db.delete(admin)
        db.commit()
        db.close()


def _stored_bytes(db, attachment_id: int) -> bytes:
    att = db.get(Attachment, attachment_id)
    return (Path(settings.UPLOADS_DIR) / att.storage_path).read_bytes()


def test_upload_without_purpose_is_stored_unchanged(ctx) -> None:
    client, _db = ctx
    content = b"hello world"

    response = client.post("/files", files={"file": ("note.txt", content, "text/plain")})

    assert response.status_code == 200
    body = response.json()
    assert body["mime"] == "text/plain"
    assert body["name"] == "note.txt"
    assert body["size_bytes"] == len(content)
    # Default TTL, not permanent -- only `category_icon` (persisted verbatim into image_url,
    # never re-signed on read) needs `exp=-1`, see 20260925_1000's migration docstring.
    assert "exp=-1" not in body["url"]


def test_upload_category_icon_purpose_returns_a_permanent_url(ctx) -> None:
    """`image_url` on content_categories/content_drafts/content_versions is saved verbatim from
    this response and never re-signed on read (unlike every other attachment usage), so a
    default-TTL link here silently 404s as "link expired" a month after being set -- exactly the
    bug 20260925_1000's migration backfills for rows that predate this fix."""
    client, _db = ctx

    response = client.post(
        "/files",
        files={"file": ("cover.png", _png_bytes(64, 64), "image/png")},
        data={"purpose": "category_icon"},
    )

    assert response.status_code == 200
    assert "exp=-1&sig=" in response.json()["url"]


def test_upload_category_icon_purpose_resizes_and_converts_to_webp(ctx) -> None:
    client, db = ctx
    source = _png_bytes(500, 300)

    response = client.post(
        "/files",
        files={"file": ("cover.png", source, "image/png")},
        data={"purpose": "category_icon"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mime"] == "image/webp"
    assert body["name"] == "cover.webp"
    assert body["size_bytes"] < len(source)

    with Image.open(io.BytesIO(_stored_bytes(db, body["id"]))) as image:
        assert image.format == "WEBP"
        assert image.width <= 128
        assert image.height <= 128


def test_upload_category_icon_purpose_never_upscales(ctx) -> None:
    client, db = ctx
    source = _png_bytes(40, 20)

    response = client.post(
        "/files",
        files={"file": ("tiny.png", source, "image/png")},
        data={"purpose": "category_icon"},
    )

    assert response.status_code == 200
    with Image.open(io.BytesIO(_stored_bytes(db, response.json()["id"]))) as image:
        assert image.width == 40
        assert image.height == 20


def test_upload_unknown_purpose_is_rejected(ctx) -> None:
    client, _db = ctx

    response = client.post(
        "/files",
        files={"file": ("cover.png", _png_bytes(64, 64), "image/png")},
        data={"purpose": "does_not_exist"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "unknown_upload_purpose"


def test_upload_category_icon_purpose_rejects_non_image(ctx) -> None:
    client, _db = ctx

    response = client.post(
        "/files",
        files={"file": ("note.txt", b"not an image", "text/plain")},
        data={"purpose": "category_icon"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "file_type"
