from __future__ import annotations

import json
from dataclasses import replace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.modules.audit.infrastructure.models import AuditLog
from app.modules.platform_admins.domain.entities import GlobalAdminIdentity
from app.modules.platform_admins.presentation import router as platform_admin_router


class InMemoryPlatformAdminRepository:
    def __init__(self) -> None:
        self.items: dict[str, GlobalAdminIdentity] = {}
        self.next_id = 1

    def find_by_max_user_id(self, max_user_id: str) -> GlobalAdminIdentity | None:
        return self.items.get(max_user_id.strip())

    def list_platform_admins(self) -> list[GlobalAdminIdentity]:
        return list(self.items.values())

    def add(self, identity: GlobalAdminIdentity) -> GlobalAdminIdentity:
        stored = replace(identity, id=self.next_id)
        self.next_id += 1
        self.items[stored.max_user_id] = stored
        return stored

    def update(self, identity: GlobalAdminIdentity) -> GlobalAdminIdentity:
        self.items[identity.max_user_id] = identity
        return identity


class AuditSession:
    def __init__(self) -> None:
        self.audit: list[AuditLog] = []
        self.commits = 0

    def add(self, value) -> None:
        if isinstance(value, AuditLog):
            self.audit.append(value)

    def commit(self) -> None:
        self.commits += 1


def _principal(role: str) -> CurrentPrincipal:
    return CurrentPrincipal(
        sub="a:5",
        role=role,
        system="max",
        user_id=None,
        admin_id=5,
    )


def _app(monkeypatch, role: str):
    app = FastAPI()
    app.include_router(platform_admin_router.router, prefix="/platform-admins")
    repository = InMemoryPlatformAdminRepository()
    session = AuditSession()
    app.dependency_overrides[get_current_principal] = lambda: _principal(role)
    app.dependency_overrides[get_db] = lambda: session
    monkeypatch.setattr(
        platform_admin_router,
        "SqlAlchemyPlatformAdminRepository",
        lambda _db: repository,
    )
    return app, repository, session


def test_platform_admin_can_provision_account_without_personal_audit_payload(monkeypatch) -> None:
    app, repository, session = _app(monkeypatch, "platform_admin")
    client = TestClient(app)

    created = client.post(
        "/platform-admins",
        json={"max_user_id": "123456", "full_name": "Иванов Иван Иванович"},
    )
    repeated = client.post(
        "/platform-admins",
        json={"max_user_id": "123456", "full_name": "Иванов Иван Иванович"},
    )
    listed = client.get("/platform-admins")

    assert created.status_code == 201
    assert created.json()["created"] is True
    assert repeated.status_code == 200
    assert repeated.json()["created"] is False
    assert len(repository.items) == 1
    assert listed.status_code == 200
    assert listed.json()[0]["max_user_id"] == "123456"
    assert session.commits == 2
    assert len(session.audit) == 2
    serialized_meta = json.dumps(session.audit[0].meta, ensure_ascii=False)
    assert "123456" not in serialized_meta
    assert "Иванов" not in serialized_meta
    assert session.audit[0].meta["target_admin_id"] == 1


@pytest.mark.parametrize("method", ["get", "post"])
def test_non_platform_admin_cannot_access_platform_admin_directory(monkeypatch, method) -> None:
    app, repository, session = _app(monkeypatch, "admin")
    client = TestClient(app)

    if method == "get":
        response = client.get("/platform-admins")
    else:
        response = client.post(
            "/platform-admins",
            json={"max_user_id": "123456", "full_name": "Иванов Иван"},
        )

    assert response.status_code == 403
    assert repository.items == {}
    assert session.audit == []
