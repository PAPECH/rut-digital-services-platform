"""POST /messages/from-student — Task 053 audit finding #5: this student-write endpoint used
to skip maintenance-mode enforcement entirely, unlike every sibling write endpoint
(submissions, files, forms, content, news, the capability routers).
"""

from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal
from app.core.errors import service_unavailable
from app.db.session import get_db
from app.main import app
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.maintenance.presentation.dependencies import enforce_user_write_available
from app.modules.tenancy.presentation.dependencies import resolve_tenant


def test_from_student_is_blocked_during_maintenance() -> None:
    bot = BotInstance(id=1, slug="default", name="Default")
    principal = CurrentPrincipal(
        sub="u:1",
        role="student",
        system="max",
        user_id=1,
        admin_id=None,
        bot_instance_id=1,
        bot_slug="default",
    )

    def blocked() -> None:
        raise service_unavailable("Технические работы", code="maintenance_mode", mode="full_stop")

    app.dependency_overrides[resolve_tenant] = lambda: bot
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[enforce_user_write_available] = blocked
    try:
        response = TestClient(app).post("/api/messages/from-student", json={"text": "hi"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "maintenance_mode"
