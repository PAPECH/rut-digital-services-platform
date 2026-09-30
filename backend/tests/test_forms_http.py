from importlib import import_module

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.forms.presentation.dependencies import FormManagerContext, require_form_manager
from app.modules.forms.presentation.router import router


class CrossTenantRepository:
    def get_draft(self, bot_instance_id: int, form_id: int):
        assert (bot_instance_id, form_id) == (2, 41)


class DummySession:
    def rollback(self):
        pass


def test_admin_form_from_another_bot_is_hidden_at_http_boundary(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/forms")
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    principal = CurrentPrincipal("a:5", "platform_admin", "max", None, 5)
    app.dependency_overrides[require_form_manager] = lambda: FormManagerContext(bot, principal)
    app.dependency_overrides[get_db] = lambda: DummySession()
    module = import_module("app.modules.forms.presentation.router")
    monkeypatch.setattr(module, "SqlAlchemyFormRepository", lambda _: CrossTenantRepository())

    response = TestClient(app).get("/forms/admin/41/draft")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "form_not_found"


def test_form_schema_rejects_unknown_personal_or_script_fields() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/forms")
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    principal = CurrentPrincipal("a:5", "platform_admin", "max", None, 5)
    app.dependency_overrides[require_form_manager] = lambda: FormManagerContext(bot, principal)
    app.dependency_overrides[get_db] = lambda: DummySession()
    response = TestClient(app).put(
        "/forms/admin/1/draft",
        json={
            "expected_revision": 0,
            "name": "Заявка",
            "description": None,
            "reply_on_accept": None,
            "fields": [
                {
                    "key": "name",
                    "type": "short_text",
                    "label": "Имя",
                    "required": True,
                    "active": True,
                    "profile_key": None,
                    "min_length": 0,
                    "max_length": 10,
                    "script": "alert(1)",
                }
            ],
            "max_user_id": "private",
        },
    )
    assert response.status_code == 422
