"""Integration tests for the admin-editable consent policy document page (Task 066) --
admin-authored HTML, stored as one extra key in consent_notice_texts, rendered on our own
public page. Follows the real-Postgres-session pattern `test_files_upload_http.py`
established for routes that commit ORM rows directly; no bot/tenant fixtures needed since
these endpoints aren't tenant-scoped (see router.py)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main  # noqa: F401 -- registers every ORM class in Base.metadata.
from app.api.deps import CurrentPrincipal, get_current_principal
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.modules.consent.infrastructure.notice_repository import (
    POLICY_DOCUMENT_HTML_KEY,
    SqlAlchemyConsentNoticeRepository,
    effective_policy_url,
)
from app.modules.consent.presentation.router import router


@pytest.fixture
def ctx():
    db = SessionLocal()
    repo = SqlAlchemyConsentNoticeRepository(db)
    snapshot = repo.get(POLICY_DOCUMENT_HTML_KEY)

    app = FastAPI()
    app.include_router(router, prefix="/consent")
    app.dependency_overrides[get_db] = lambda: db

    def as_role(role: str) -> None:
        app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
            sub="a:1", role=role, system="max", user_id=None, admin_id=1
        )

    as_role("platform_admin")
    client = TestClient(app)
    try:
        yield client, db, as_role
    finally:
        db.rollback()
        if snapshot is None:
            repo.delete(POLICY_DOCUMENT_HTML_KEY)
        else:
            repo.upsert(POLICY_DOCUMENT_HTML_KEY, snapshot)
        db.commit()
        db.close()


def test_effective_policy_url_is_always_our_own_page() -> None:
    assert effective_policy_url() == f"{settings.PUBLIC_API_URL}/api/consent/policy-document"


def test_public_page_renders_admin_html(ctx) -> None:
    client, db, _as = ctx
    repo = SqlAlchemyConsentNoticeRepository(db)
    repo.upsert(POLICY_DOCUMENT_HTML_KEY, "<p>Текст политики <b>жирным</b>.</p>")
    db.commit()

    response = client.get("/consent/policy-document")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<p>Текст политики <b>жирным</b>.</p>" in response.text
    assert "<html" in response.text.lower()


def test_public_page_shows_placeholder_when_unset(ctx) -> None:
    client, db, _as = ctx
    repo = SqlAlchemyConsentNoticeRepository(db)
    repo.delete(POLICY_DOCUMENT_HTML_KEY)
    db.commit()

    response = client.get("/consent/policy-document")

    assert response.status_code == 200
    assert "не заполнен" in response.text


def test_admin_get_and_put_round_trip(ctx) -> None:
    client, db, _as = ctx

    put_response = client.put("/consent/admin/policy-document", json={"value": "<p>Новый текст</p>"})
    assert put_response.status_code == 200
    assert put_response.json() == {"value": "<p>Новый текст</p>"}

    get_response = client.get("/consent/admin/policy-document")
    assert get_response.status_code == 200
    assert get_response.json() == {"value": "<p>Новый текст</p>"}

    assert "<p>Новый текст</p>" in client.get("/consent/policy-document").text


@pytest.mark.parametrize("role", ["student", "employee", "admin"])
def test_non_platform_admin_forbidden(ctx, role: str) -> None:
    client, db, as_role = ctx
    as_role(role)

    assert client.get("/consent/admin/policy-document").status_code == 403
    assert (
        client.put("/consent/admin/policy-document", json={"value": "x"}).status_code == 403
    )
