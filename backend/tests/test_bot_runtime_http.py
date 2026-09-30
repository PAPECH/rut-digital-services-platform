from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.errors import unauthorized
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.bot_instances.infrastructure.models import (
    BotInstanceRecord,
    BotRuntimeRecord,
)
from app.modules.bot_instances.presentation import runtime_router
from app.modules.bot_instances.presentation.runtime_router import router
from app.modules.bot_instances.presentation.runtime_schemas import (
    RuntimeCredentialRequest,
)
from app.modules.tenancy.presentation.dependencies import resolve_tenant


class RuntimeSession:
    def __init__(self, bot_id: int) -> None:
        self.bot = BotInstanceRecord(id=bot_id, slug=f"bot-{bot_id}", name="Бот")
        self.runtime = BotRuntimeRecord(
            bot_instance_id=bot_id,
            credential_source=None,
            credential_env_key=None,
            mode="polling",
        )
        self.commits = 0

    def get(self, model, key):
        if model is BotInstanceRecord and key == self.bot.id:
            return self.bot
        if model is BotRuntimeRecord and key == self.runtime.bot_instance_id:
            return self.runtime
        return None

    def add(self, _value) -> None:
        pass

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, _value) -> None:
        pass


def _app(bot_id: int, session: RuntimeSession) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/instances")
    app.dependency_overrides[resolve_tenant] = lambda: BotInstance(
        id=bot_id,
        slug=f"bot-{bot_id}",
        name="Бот",
    )
    app.dependency_overrides[get_db] = lambda: session
    return app


def test_heartbeat_stores_actual_identity_for_resolved_bot(monkeypatch) -> None:
    session = RuntimeSession(bot_id=2)
    app = _app(bot_id=2, session=session)
    authorized_bot_ids: list[int] = []

    def authorize(_db, bot_id, _runtime_token, _legacy_token) -> None:
        authorized_bot_ids.append(bot_id)

    monkeypatch.setattr(runtime_router, "authorize_bot_runtime", authorize)

    response = TestClient(app).post(
        "/instances/runtime/heartbeat",
        headers={"X-Bot-Runtime-Token": "bot-2-token"},
        json={"username": "rut_hr_bot", "user_id": "987654", "version": "1.2.0"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "rut_hr_bot"
    assert response.json()["max_bot_id"] == "987654"
    assert "expected_username" not in response.json()
    assert authorized_bot_ids == [2]
    assert session.runtime.username == "rut_hr_bot"
    assert session.runtime.max_bot_id == "987654"
    assert session.commits == 1


def test_failed_identity_refresh_preserves_last_confirmed_bot(monkeypatch) -> None:
    session = RuntimeSession(bot_id=2)
    session.runtime.username = "rut_hr_bot"
    session.runtime.max_bot_id = "987654"
    app = _app(bot_id=2, session=session)
    monkeypatch.setattr(runtime_router, "authorize_bot_runtime", lambda *_args: None)

    response = TestClient(app).post(
        "/instances/runtime/heartbeat",
        json={"error_code": "max_get_me_failed", "version": "1.2.1"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "rut_hr_bot"
    assert response.json()["max_bot_id"] == "987654"
    assert response.json()["last_error_code"] == "max_get_me_failed"


def test_runtime_token_from_another_bot_is_denied(monkeypatch) -> None:
    session = RuntimeSession(bot_id=2)
    app = _app(bot_id=2, session=session)

    def deny_other_bot(_db, bot_id, runtime_token, _legacy_token) -> None:
        assert bot_id == 2
        assert runtime_token == "bot-1-token"
        raise unauthorized("Неверный runtime token", code="invalid_bot_runtime_token")

    monkeypatch.setattr(runtime_router, "authorize_bot_runtime", deny_other_bot)

    response = TestClient(app).post(
        "/instances/runtime/heartbeat",
        headers={"X-Bot-Runtime-Token": "bot-1-token"},
        json={"username": "wrong_bot", "user_id": "111"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_bot_runtime_token"
    assert session.runtime.username is None
    assert session.runtime.max_bot_id is None
    assert session.commits == 0


def test_runtime_credential_contract_rejects_removed_expected_username() -> None:
    try:
        RuntimeCredentialRequest.model_validate(
            {
                "source": "environment",
                "credential_env_key": "MAX_BOT_TOKEN_HR",
                "expected_username": "legacy_bot",
                "mode": "polling",
            }
        )
    except ValidationError as error:
        assert error.errors()[0]["type"] == "extra_forbidden"
    else:
        raise AssertionError("expected_username must not be accepted")
