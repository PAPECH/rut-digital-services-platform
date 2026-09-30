from __future__ import annotations

from importlib import import_module

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal, require_student
from app.db.session import get_db
from app.modules.knowledge_base.presentation.faq_router import router
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.tenancy.presentation.dependencies import require_tenant_access
from app.services.log_action import ActionType


class EmptyScalarResult:
    def scalars(self):
        return []


class ReadOnlyFaqSession:
    def execute(self, _statement):
        return EmptyScalarResult()


def _student(bot_instance_id: int = 1) -> CurrentPrincipal:
    return CurrentPrincipal(
        sub="u:17",
        role="student",
        system="max",
        user_id=17,
        admin_id=None,
        bot_instance_id=bot_instance_id,
        bot_slug=f"bot-{bot_instance_id}",
    )


def test_faq_prefetch_does_not_record_open_event(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/faq")
    principal = _student()
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: ReadOnlyFaqSession()
    faq_module = import_module("app.modules.knowledge_base.presentation.faq_router")

    def unexpected_log(**_kwargs):
        raise AssertionError("FAQ prefetch must not emit faq_open")

    monkeypatch.setattr(faq_module, "log_action", unexpected_log)

    response = TestClient(app).get("/faq")

    assert response.status_code == 200
    assert response.json() == []


def test_explicit_faq_open_event_uses_resolved_tenant(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/faq")
    principal = _student(bot_instance_id=1)
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app.dependency_overrides[require_student] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: object()
    captured: dict[str, object] = {}
    faq_module = import_module("app.modules.knowledge_base.presentation.faq_router")

    def capture_log(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(faq_module, "log_action", capture_log)

    response = TestClient(app).post("/faq/events/open")

    assert response.status_code == 204
    assert captured["bot_instance_id"] == 1
    assert captured["user_id"] == 17
    assert captured["action_type"] == ActionType.FAQ_OPEN
    assert captured["commit"] is True
    assert "description" not in captured
    assert "payload" not in captured


def test_faq_open_event_denies_user_token_from_another_tenant() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/faq")
    principal = _student(bot_instance_id=1)
    selected_bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    app.dependency_overrides[require_student] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: require_tenant_access(
        bot=selected_bot,
        principal=principal,
        db=None,
    )
    app.dependency_overrides[get_db] = lambda: object()

    response = TestClient(app).post("/faq/events/open")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_mismatch"
