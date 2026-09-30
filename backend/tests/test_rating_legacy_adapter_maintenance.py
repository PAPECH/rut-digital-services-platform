"""api/routes/rating.py — the deprecated admission-rating compat adapter calls the real
capability handlers (admission_rating/presentation/router.py) as plain Python functions
instead of going through that router's own registration, so the maintenance-mode
dependencies() declared THERE never ran for requests made through this legacy path
(Task 053 audit finding #2). Mirrors test_admission_rating_capability.py's
test_full_stop_dependency_blocks_lookup pattern against the real capability router, proving
the legacy alias now enforces the same gate.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.rating import router
from app.core.errors import service_unavailable
from app.modules.maintenance.presentation.dependencies import (
    enforce_user_access_available,
    enforce_user_write_available,
)


def _blocked() -> None:
    raise service_unavailable("Технические работы", code="maintenance_mode", mode="full_stop")


def test_legacy_lookup_is_blocked_during_maintenance() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/rating")
    app.dependency_overrides[enforce_user_access_available] = _blocked

    response = TestClient(app).get("/rating/lookup?display_name=ABC")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "maintenance_mode"


def test_legacy_subscription_is_blocked_during_maintenance() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/rating")
    app.dependency_overrides[enforce_user_access_available] = _blocked

    response = TestClient(app).get("/rating/subscription")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "maintenance_mode"


def test_legacy_subscribe_is_blocked_during_maintenance() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/rating")
    app.dependency_overrides[enforce_user_write_available] = _blocked

    response = TestClient(app).post("/rating/subscribe", json={"display_name": "ABC"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "maintenance_mode"


def test_legacy_unsubscribe_is_blocked_during_maintenance() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/rating")
    app.dependency_overrides[enforce_user_write_available] = _blocked

    response = TestClient(app).post("/rating/unsubscribe", json={"display_name": "ABC"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "maintenance_mode"
