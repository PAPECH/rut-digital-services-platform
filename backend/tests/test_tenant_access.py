import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal
from app.core.errors import ApiError
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.tenancy.presentation.dependencies import require_tenant_access, resolve_tenant


def test_student_token_cannot_cross_bot_boundary() -> None:
    bot = BotInstance(id=2, slug="hr-bot", name="Кадровые сервисы")
    principal = CurrentPrincipal(
        sub="u:17",
        role="student",
        system="max",
        user_id=17,
        admin_id=None,
        bot_instance_id=1,
        bot_slug="other-bot",
    )

    with pytest.raises(ApiError) as error:
        require_tenant_access(bot=bot, principal=principal, db=None)  # type: ignore[arg-type]

    assert error.value.status_code == 403
    assert error.value.detail["code"] == "tenant_mismatch"


def test_student_cross_tenant_request_is_denied_at_http_boundary() -> None:
    app = FastAPI()
    bot = BotInstance(id=2, slug="hr-bot", name="Кадровые сервисы")
    principal = CurrentPrincipal(
        sub="u:17",
        role="student",
        system="max",
        user_id=17,
        admin_id=None,
        bot_instance_id=1,
        bot_slug="other-bot",
    )

    @app.get("/tenant-check")
    def tenant_check(_: BotInstance = Depends(require_tenant_access)) -> dict[str, bool]:
        return {"ok": True}

    app.dependency_overrides[resolve_tenant] = lambda: bot
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = lambda: None

    response = TestClient(app).get("/tenant-check")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_mismatch"
