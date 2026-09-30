from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.modules.support_chat.presentation import ws_router as ws_router_module
from app.modules.support_chat.presentation.ws_router import router
from app.services.ws_hub import platform_admin_room, staff_room, user_room


class _ScalarResult:
    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeWsSession:
    """Fakes the ordered sequence of `db.execute(...).scalar_one_or_none()` calls
    `ws_chat` makes -- one entry per call, in the order the router makes them."""

    def __init__(self, results: list) -> None:
        self._results = list(results)

    def execute(self, _stmt):
        return _ScalarResult(self._results.pop(0))

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


class _Bot:
    def __init__(self, id: int) -> None:
        self.id = id


class _Membership:
    def __init__(self, *, is_active: bool = True, ban_app: bool = False) -> None:
        self.is_active = is_active
        self.ban_app = ban_app


def _app(monkeypatch, results: list) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    monkeypatch.setattr(ws_router_module, "SessionLocal", lambda: FakeWsSession(results))
    return app


def _student_token(*, user_pk: int = 1, bot_instance_id: int = 2) -> str:
    return create_access_token(
        {"sub": f"u:{user_pk}", "role": "student", "user_pk": user_pk, "bot_instance_id": bot_instance_id}
    )


def _staff_token(*, role: str = "admin", admin_id: int = 5) -> str:
    return create_access_token({"sub": f"a:{admin_id}", "role": role, "admin_id": admin_id})


# Every rejection below happens before the router calls `websocket.accept()`, so Starlette's
# test client raises WebSocketDisconnect out of `websocket_connect(...).__enter__()` rather
# than letting the close frame be read normally -- assert on the raised exception's code.


def test_rejects_invalid_token(monkeypatch) -> None:
    app = _app(monkeypatch, results=[])
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/chat?token=garbage"):
            pass
    assert exc.value.code == 4401


def test_student_missing_claims_is_unauthorized(monkeypatch) -> None:
    token = create_access_token({"sub": "u:1", "role": "student"})
    app = _app(monkeypatch, results=[])
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat?token={token}"):
            pass
    assert exc.value.code == 4401


def test_student_without_active_membership_is_forbidden(monkeypatch) -> None:
    token = _student_token(user_pk=1, bot_instance_id=2)
    app = _app(monkeypatch, results=[None])
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat?token={token}"):
            pass
    assert exc.value.code == 4403


def test_student_with_active_membership_joins_own_room(monkeypatch) -> None:
    token = _student_token(user_pk=1, bot_instance_id=2)
    app = _app(monkeypatch, results=[_Membership(is_active=True, ban_app=False)])
    client = TestClient(app)

    with client.websocket_connect(f"/ws/chat?token={token}") as ws:
        ready = ws.receive_json()

    assert ready == {"type": "ready", "rooms": [user_room(1, 2)]}


def test_staff_without_bot_slug_is_forbidden(monkeypatch) -> None:
    token = _staff_token()
    app = _app(monkeypatch, results=[])
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat?token={token}"):
            pass
    assert exc.value.code == 4403


def test_staff_unknown_bot_slug_is_forbidden(monkeypatch) -> None:
    token = _staff_token()
    app = _app(monkeypatch, results=[None])
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat?token={token}&bot_slug=missing-bot"):
            pass
    assert exc.value.code == 4403


def test_staff_without_bot_access_is_forbidden(monkeypatch) -> None:
    token = _staff_token(role="admin", admin_id=5)
    app = _app(monkeypatch, results=[_Bot(id=2), None])
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat?token={token}&bot_slug=bot-2"):
            pass
    assert exc.value.code == 4403


def test_staff_with_bot_access_joins_staff_room_only(monkeypatch) -> None:
    token = _staff_token(role="admin", admin_id=5)
    app = _app(monkeypatch, results=[_Bot(id=2), 999])
    client = TestClient(app)

    with client.websocket_connect(f"/ws/chat?token={token}&bot_slug=bot-2") as ws:
        ready = ws.receive_json()

    assert ready == {"type": "ready", "rooms": [staff_room(2)]}


def test_platform_admin_joins_staff_and_platform_admin_rooms(monkeypatch) -> None:
    token = _staff_token(role="platform_admin", admin_id=1)
    app = _app(monkeypatch, results=[_Bot(id=2)])
    client = TestClient(app)

    with client.websocket_connect(f"/ws/chat?token={token}&bot_slug=bot-2") as ws:
        ready = ws.receive_json()

    assert ready == {"type": "ready", "rooms": [staff_room(2), platform_admin_room(2)]}


def test_staff_with_user_pk_also_joins_that_conversation_room(monkeypatch) -> None:
    token = _staff_token(role="admin", admin_id=5)
    app = _app(monkeypatch, results=[_Bot(id=2), 999, 42])
    client = TestClient(app)

    with client.websocket_connect(f"/ws/chat?token={token}&bot_slug=bot-2&user_pk=7") as ws:
        ready = ws.receive_json()

    assert ready == {"type": "ready", "rooms": [staff_room(2), user_room(7, 2)]}
