from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, require_admin
from app.core.errors import forbidden
from app.db.session import get_db
from app.modules.audit.domain.entities import AuditEntry
from app.modules.audit.presentation import router as audit_router_module
from app.modules.audit.presentation.router import router
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.tenancy.presentation.dependencies import require_tenant_access


class FakeAuditLogRepository:
    def __init__(self, entries_by_bot: dict[int, list[AuditEntry]]) -> None:
        self._entries_by_bot = entries_by_bot

    def list_for_bot(self, bot_instance_id: int, *, limit: int, offset: int) -> list[AuditEntry]:
        entries = self._entries_by_bot.get(bot_instance_id, [])
        return entries[offset : offset + limit]


def _entry(id: int, *, admin_id: int | None = 1, admin_name: str | None = "Alice") -> AuditEntry:
    return AuditEntry(
        id=id,
        created_at=datetime(2026, 1, id, tzinfo=timezone.utc),
        admin_id=admin_id,
        admin_name=admin_name,
        method="POST",
        path="/api/admins",
        status_code=201,
        duration_ms=12,
        meta=None,
    )


def _admin_principal() -> CurrentPrincipal:
    return CurrentPrincipal(sub="a:1", role="admin", system="max", user_id=None, admin_id=1)


def _app(*, entries_by_bot: dict[int, list[AuditEntry]], monkeypatch, bot_id: int = 2) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/audit")
    bot = BotInstance(id=bot_id, slug=f"bot-{bot_id}", name=f"Бот {bot_id}")
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: None
    monkeypatch.setattr(
        audit_router_module,
        "SqlAlchemyAuditLogRepository",
        lambda _db: FakeAuditLogRepository(entries_by_bot),
    )
    return app


def test_list_audit_entries_without_auth_is_unauthorized(monkeypatch) -> None:
    app = _app(entries_by_bot={}, monkeypatch=monkeypatch)

    response = TestClient(app).get("/audit")

    assert response.status_code == 401


def test_list_audit_entries_denies_cross_tenant_access(monkeypatch) -> None:
    app = _app(entries_by_bot={}, monkeypatch=monkeypatch)
    app.dependency_overrides[require_admin] = lambda: _admin_principal()

    def deny() -> BotInstance:
        raise forbidden("No bot access", code="tenant_access_denied")

    app.dependency_overrides[require_tenant_access] = deny

    response = TestClient(app).get("/audit")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_access_denied"


def test_list_audit_entries_scoped_to_resolved_bot_only(monkeypatch) -> None:
    entries_by_bot = {1: [_entry(1)], 2: [_entry(2), _entry(3)]}
    app = _app(entries_by_bot=entries_by_bot, monkeypatch=monkeypatch, bot_id=2)
    app.dependency_overrides[require_admin] = lambda: _admin_principal()

    response = TestClient(app).get("/audit")

    assert response.status_code == 200
    ids = [row["id"] for row in response.json()]
    assert ids == [2, 3]


def test_list_audit_entries_admin_name_is_null_without_matching_admin(monkeypatch) -> None:
    entries_by_bot = {2: [_entry(1, admin_id=99, admin_name=None)]}
    app = _app(entries_by_bot=entries_by_bot, monkeypatch=monkeypatch, bot_id=2)
    app.dependency_overrides[require_admin] = lambda: _admin_principal()

    response = TestClient(app).get("/audit")

    assert response.status_code == 200
    body = response.json()[0]
    assert body["admin_id"] == 99
    assert body["admin_name"] is None


def test_list_audit_entries_respects_limit_and_offset(monkeypatch) -> None:
    entries_by_bot = {2: [_entry(1), _entry(2), _entry(3)]}
    app = _app(entries_by_bot=entries_by_bot, monkeypatch=monkeypatch, bot_id=2)
    app.dependency_overrides[require_admin] = lambda: _admin_principal()

    response = TestClient(app).get("/audit", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    ids = [row["id"] for row in response.json()]
    assert ids == [2]
