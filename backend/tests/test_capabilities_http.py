import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal, require_student
from app.core.errors import ApiError
from app.db.session import get_db
from app.modules.admins.infrastructure.models import Admin
from app.models.enums import AdminRoleEnum
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.bot_instances.infrastructure.models import AdminBotAccessRecord
from app.modules.capabilities.presentation.dependencies import require_capability_manager
from app.modules.capabilities.presentation.router import router
from app.modules.maintenance.presentation.dependencies import enforce_user_access_available
from app.modules.tenancy.presentation.dependencies import require_tenant_access


class CapabilityAccessDb:
    """Fake Session — admin_has_bot_permission (Task 053) resolves permission through
    SqlAlchemyStaffAccessRepository.get_by_staff, a join returning (access, admin), not
    the older single-column scalar query — one_or_none() below matches that shape."""

    def __init__(self, access_id: int | None) -> None:
        self.access_id = access_id

    def execute(self, _statement):
        return self

    def scalar_one_or_none(self):
        return self.access_id

    def one_or_none(self):
        if self.access_id is None:
            return None
        access = AdminBotAccessRecord(
            id=self.access_id,
            bot_instance_id=1,
            admin_id=5,
            can_manage_capabilities=True,
        )
        admin = Admin(
            id=5, max_user_id="max:5", full_name="Staff", role=AdminRoleEnum.admin, is_active=True
        )
        return (access, admin)


def _staff_principal(*, role: str = "admin") -> CurrentPrincipal:
    return CurrentPrincipal(
        sub="a:5",
        role=role,
        system="max",
        user_id=None,
        admin_id=5,
        bot_instance_id=1,
        bot_slug="bot-1",
    )


def test_capability_manager_permission_is_rechecked() -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    principal = _staff_principal()

    context = require_capability_manager(
        bot=bot,
        principal=principal,
        db=CapabilityAccessDb(11),
    )
    assert context.bot.id == 1

    with pytest.raises(ApiError) as error:
        require_capability_manager(
            bot=bot,
            principal=principal,
            db=CapabilityAccessDb(None),
        )
    assert error.value.detail["code"] == "capability_access_denied"


def test_platform_admin_does_not_require_delegated_capability_permission() -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    principal = _staff_principal(role="platform_admin")

    context = require_capability_manager(bot=bot, principal=principal, db=None)

    assert context.bot.id == 2


def test_staff_token_cannot_select_another_bot_for_capability_admin() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/capabilities")
    selected_bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    principal = CurrentPrincipal(
        sub="a:5",
        role="admin",
        system="max",
        user_id=None,
        admin_id=5,
        bot_instance_id=1,
        bot_slug="bot-1",
    )

    class NoTenantAccessDb:
        def execute(self, _statement):
            return self

        def scalar_one_or_none(self):
            return None

        def one_or_none(self):
            return None

    app.dependency_overrides[require_tenant_access] = lambda: require_tenant_access(
        bot=selected_bot,
        principal=principal,
        db=NoTenantAccessDb(),
    )
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = lambda: None

    response = TestClient(app).get("/capabilities/admin")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_access_denied"


def test_capability_view_event_rejects_personal_or_free_form_payload() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/capabilities")
    principal = CurrentPrincipal("u:7", "student", "max", 7, None, 1, "bot-1")
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app.dependency_overrides[require_student] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[enforce_user_access_available] = lambda: None
    app.dependency_overrides[get_db] = lambda: None
    response = TestClient(app).post(
        "/capabilities/request_status/events/view-open",
        json={
            "installation_id": 1,
            "view_key": "lookup",
            "request_number": "PERSONAL-123",
            "max_user_id": "private",
        },
    )
    assert response.status_code == 422
