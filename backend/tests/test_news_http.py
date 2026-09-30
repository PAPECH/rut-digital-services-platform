from __future__ import annotations

from importlib import import_module

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal, require_student
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.news.presentation.dependencies import require_news_manager
from app.modules.news.presentation.router import router
from app.modules.tenancy.presentation.dependencies import require_tenant_access
from app.services.log_action import ActionType


class EmptyScalarResult:
    def scalars(self):
        return []

    def scalar_one_or_none(self):
        return None


class ReadOnlyNewsSession:
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


def _bot_admin(bot_instance_id: int = 1) -> CurrentPrincipal:
    return CurrentPrincipal(
        sub="a:5",
        role="admin",
        system="max",
        user_id=None,
        admin_id=5,
        bot_instance_id=bot_instance_id,
        bot_slug=f"bot-{bot_instance_id}",
    )


def test_list_news_does_not_include_inactive_for_students() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/news")
    principal = _student()
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: ReadOnlyNewsSession()

    response = TestClient(app).get("/news")

    assert response.status_code == 200
    assert response.json() == []


def test_explicit_news_open_event_uses_resolved_tenant(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/news")
    principal = _student(bot_instance_id=1)
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app.dependency_overrides[require_student] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: object()
    captured: dict[str, object] = {}
    news_module = import_module("app.modules.news.presentation.router")

    def capture_log(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(news_module, "log_action", capture_log)

    response = TestClient(app).post("/news/events/open")

    assert response.status_code == 204
    assert captured["bot_instance_id"] == 1
    assert captured["user_id"] == 17
    assert captured["action_type"] == ActionType.NEWS_OPEN
    assert captured["commit"] is True


def test_news_item_open_event_carries_news_id(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/news")
    principal = _student(bot_instance_id=1)
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app.dependency_overrides[require_student] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: object()
    captured: dict[str, object] = {}
    news_module = import_module("app.modules.news.presentation.router")
    monkeypatch.setattr(news_module, "log_action", lambda **kwargs: captured.update(kwargs))

    response = TestClient(app).post("/news/42/events/open")

    assert response.status_code == 204
    assert captured["action_type"] == ActionType.NEWS_ITEM_OPEN
    assert captured["news_id"] == 42


def test_news_open_event_denies_user_token_from_another_tenant() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/news")
    principal = _student(bot_instance_id=1)
    selected_bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    app.dependency_overrides[require_student] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: require_tenant_access(
        bot=selected_bot,
        principal=principal,
        db=None,
    )
    app.dependency_overrides[get_db] = lambda: object()

    response = TestClient(app).post("/news/events/open")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_mismatch"


class DeniedAccessSession:
    """Simulates a bot-admin with no can_manage_content permission for this bot."""

    def execute(self, _statement):
        class _Result:
            def scalar_one_or_none(self_inner):
                return None

            def one_or_none(self_inner):
                return None

        return _Result()


def test_create_news_denies_admin_without_can_manage_content() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/news")
    principal = _bot_admin(bot_instance_id=1)
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: DeniedAccessSession()

    response = TestClient(app).post(
        "/news",
        json={
            "title": "Заголовок",
            "body_blocks": [{"id": "p1", "type": "paragraph", "text": "Текст"}],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "news_access_denied"


def test_create_news_rejects_navigational_block_in_body() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/news")
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    principal = _bot_admin(bot_instance_id=1)
    app.dependency_overrides[require_news_manager] = lambda: import_module(
        "app.modules.news.presentation.dependencies"
    ).NewsManagerContext(bot=bot, principal=principal)

    response = TestClient(app).post(
        "/news",
        json={
            "title": "Заголовок",
            "body_blocks": [{"id": "grid", "type": "category_grid"}],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_news_body"
