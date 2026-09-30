from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, require_platform_admin
from app.db.session import get_db
from app.modules.admins.application.admin_use_cases import (
    AdminAccountAlreadyExists,
    CannotModifyOwnPrivileges,
    CreateAdminAccount,
    DeleteAdminAccount,
    UpdateAdminAccount,
)
from app.modules.admins.domain.admin_account import AdminAccount
from app.modules.admins.presentation import router as admins_router_module
from app.modules.admins.presentation.router import router


class FakeAdminAccountRepository:
    def __init__(self, accounts: dict[int, AdminAccount]) -> None:
        self._accounts = accounts
        self._next_id = (max(self._accounts) + 1) if self._accounts else 1

    def list_all(self) -> list[AdminAccount]:
        return sorted(self._accounts.values(), key=lambda a: a.id)

    def find_by_max_user_id(self, max_user_id: str) -> AdminAccount | None:
        for account in self._accounts.values():
            if account.max_user_id == max_user_id:
                return account
        return None

    def get(self, admin_id: int) -> AdminAccount | None:
        return self._accounts.get(admin_id)

    def add(self, account: AdminAccount) -> AdminAccount:
        new_id = self._next_id
        self._next_id += 1
        created = AdminAccount(
            id=new_id,
            max_user_id=account.max_user_id,
            full_name=account.full_name,
            role=account.role,
            is_active=account.is_active,
        )
        self._accounts[new_id] = created
        return created

    def update(self, admin_id: int, changes: dict[str, object]) -> AdminAccount:
        current = self._accounts[admin_id]
        updated = AdminAccount(
            id=current.id,
            max_user_id=current.max_user_id,
            full_name=changes.get("full_name", current.full_name),
            role=changes.get("role", current.role),
            is_active=changes.get("is_active", current.is_active),
        )
        self._accounts[admin_id] = updated
        return updated

    def delete(self, admin_id: int) -> None:
        del self._accounts[admin_id]


def _principal(*, admin_id: int, role: str = "platform_admin") -> CurrentPrincipal:
    return CurrentPrincipal(
        sub=f"a:{admin_id}", role=role, system="max", user_id=None, admin_id=admin_id
    )


def _app(
    *, accounts: dict[int, AdminAccount], monkeypatch, actor: CurrentPrincipal | None
) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/admins")
    app.dependency_overrides[get_db] = lambda: None
    if actor is not None:
        app.dependency_overrides[require_platform_admin] = lambda: actor
    monkeypatch.setattr(
        admins_router_module,
        "SqlAlchemyAdminAccountRepository",
        lambda _db: FakeAdminAccountRepository(accounts),
    )
    return app


def _admin(id: int, *, role: str = "employee", is_active: bool = True, max_user_id: str | None = None) -> AdminAccount:
    return AdminAccount(
        id=id,
        max_user_id=max_user_id or f"u{id}",
        full_name=f"Admin {id}",
        role=role,
        is_active=is_active,
    )


# --- HTTP boundary -----------------------------------------------------------------------


def test_list_admins_without_auth_is_unauthorized(monkeypatch) -> None:
    app = _app(accounts={}, monkeypatch=monkeypatch, actor=None)

    response = TestClient(app).get("/admins")

    assert response.status_code == 401


def test_create_admin_happy_path(monkeypatch) -> None:
    app = _app(accounts={}, monkeypatch=monkeypatch, actor=_principal(admin_id=1))

    response = TestClient(app).post(
        "/admins", json={"max_user_id": "new-user", "full_name": "New Admin"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["max_user_id"] == "new-user"
    assert body["role"] == "employee"
    assert body["is_active"] is True


def test_create_admin_rejects_blank_fields(monkeypatch) -> None:
    app = _app(accounts={}, monkeypatch=monkeypatch, actor=_principal(admin_id=1))

    response = TestClient(app).post("/admins", json={"max_user_id": "  ", "full_name": "X"})

    assert response.status_code == 400


def test_create_admin_rejects_duplicate_max_user_id(monkeypatch) -> None:
    app = _app(
        accounts={1: _admin(1, max_user_id="dup")}, monkeypatch=monkeypatch, actor=_principal(admin_id=1)
    )

    response = TestClient(app).post("/admins", json={"max_user_id": "dup", "full_name": "Y"})

    assert response.status_code == 409


def test_create_platform_admin_role_requires_platform_admin_actor(monkeypatch) -> None:
    app = _app(
        accounts={},
        monkeypatch=monkeypatch,
        actor=_principal(admin_id=1, role="admin"),
    )

    response = TestClient(app).post(
        "/admins",
        json={"max_user_id": "new-user", "full_name": "New", "role": "platform_admin"},
    )

    assert response.status_code == 403


def test_patch_admin_not_found(monkeypatch) -> None:
    app = _app(accounts={}, monkeypatch=monkeypatch, actor=_principal(admin_id=1))

    response = TestClient(app).patch("/admins/999", json={"full_name": "X"})

    assert response.status_code == 404


def test_patch_admin_rejects_self_deactivation(monkeypatch) -> None:
    app = _app(
        accounts={1: _admin(1)}, monkeypatch=monkeypatch, actor=_principal(admin_id=1, role="admin")
    )

    response = TestClient(app).patch("/admins/1", json={"is_active": False})

    assert response.status_code == 400


def test_patch_admin_rejects_self_role_change(monkeypatch) -> None:
    app = _app(
        accounts={1: _admin(1, role="admin")},
        monkeypatch=monkeypatch,
        actor=_principal(admin_id=1, role="admin"),
    )

    response = TestClient(app).patch("/admins/1", json={"role": "employee"})

    assert response.status_code == 400


def test_patch_admin_allows_changing_another_account(monkeypatch) -> None:
    app = _app(
        accounts={1: _admin(1), 2: _admin(2)},
        monkeypatch=monkeypatch,
        actor=_principal(admin_id=1, role="admin"),
    )

    response = TestClient(app).patch("/admins/2", json={"is_active": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_patch_admin_platform_role_requires_platform_admin_actor(monkeypatch) -> None:
    app = _app(
        accounts={1: _admin(1, role="admin"), 2: _admin(2, role="platform_admin")},
        monkeypatch=monkeypatch,
        actor=_principal(admin_id=1, role="admin"),
    )

    response = TestClient(app).patch("/admins/2", json={"full_name": "Renamed"})

    assert response.status_code == 403


def test_delete_admin_not_found(monkeypatch) -> None:
    app = _app(accounts={}, monkeypatch=monkeypatch, actor=_principal(admin_id=1))

    response = TestClient(app).delete("/admins/999")

    assert response.status_code == 404


def test_delete_admin_rejects_self_delete(monkeypatch) -> None:
    app = _app(
        accounts={1: _admin(1)}, monkeypatch=monkeypatch, actor=_principal(admin_id=1, role="admin")
    )

    response = TestClient(app).delete("/admins/1")

    assert response.status_code == 400


def test_delete_admin_platform_role_requires_platform_admin_actor(monkeypatch) -> None:
    app = _app(
        accounts={1: _admin(1, role="admin"), 2: _admin(2, role="platform_admin")},
        monkeypatch=monkeypatch,
        actor=_principal(admin_id=1, role="admin"),
    )

    response = TestClient(app).delete("/admins/2")

    assert response.status_code == 403


def test_delete_admin_happy_path(monkeypatch) -> None:
    accounts = {1: _admin(1), 2: _admin(2)}
    app = _app(accounts=accounts, monkeypatch=monkeypatch, actor=_principal(admin_id=1, role="admin"))

    response = TestClient(app).delete("/admins/2")

    assert response.status_code == 204
    assert TestClient(app).get("/admins").json() == [
        {"id": 1, "max_user_id": "u1", "full_name": "Admin 1", "role": "employee", "is_active": True}
    ]


# --- domain/application unit tests --------------------------------------------------------


def test_create_admin_account_rejects_duplicate() -> None:
    repo = FakeAdminAccountRepository({1: _admin(1, max_user_id="dup")})

    with pytest.raises(AdminAccountAlreadyExists):
        CreateAdminAccount(repo).execute(
            max_user_id="dup", full_name="Y", role="employee", is_active=True
        )


def test_update_admin_account_rejects_self_deactivate() -> None:
    repo = FakeAdminAccountRepository({1: _admin(1)})

    with pytest.raises(CannotModifyOwnPrivileges):
        UpdateAdminAccount(repo).execute(1, {"is_active": False}, actor_admin_id=1)


def test_update_admin_account_rejects_self_role_change() -> None:
    repo = FakeAdminAccountRepository({1: _admin(1, role="admin")})

    with pytest.raises(CannotModifyOwnPrivileges):
        UpdateAdminAccount(repo).execute(1, {"role": "employee"}, actor_admin_id=1)


def test_update_admin_account_allows_changing_a_different_account() -> None:
    repo = FakeAdminAccountRepository({1: _admin(1), 2: _admin(2)})

    updated = UpdateAdminAccount(repo).execute(2, {"is_active": False}, actor_admin_id=1)

    assert updated.is_active is False


def test_delete_admin_account_rejects_self_delete() -> None:
    repo = FakeAdminAccountRepository({1: _admin(1)})

    with pytest.raises(CannotModifyOwnPrivileges):
        DeleteAdminAccount(repo).execute(1, actor_admin_id=1)
