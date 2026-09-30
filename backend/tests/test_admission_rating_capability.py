from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, require_student
from app.core.errors import service_unavailable
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.capabilities.admission_rating.application.use_cases import (
    LookupAdmissionRating,
    SetAdmissionRatingSubscription,
    rating_change_notification_payload,
)
from app.modules.capabilities.admission_rating.domain.change_policy import (
    has_meaningful_rating_change,
)
from app.modules.capabilities.admission_rating.domain.config import (
    InvalidAdmissionRatingConfig,
    validate_admission_rating_config,
)
from app.modules.capabilities.admission_rating.domain.entities import (
    RatingEntry,
    RatingSubscription,
)
from app.modules.capabilities.admission_rating.domain.identity import (
    applicant_code_hash,
    normalize_applicant_code,
)
from app.modules.capabilities.admission_rating.infrastructure import provider as provider_module
from app.modules.capabilities.admission_rating.infrastructure.parser import (
    parse_plans,
    parse_ratings,
)
from app.modules.capabilities.admission_rating.infrastructure.provider import (
    RutAdmissionProvider,
    RutAdmissionProviderError,
)
from app.modules.capabilities.admission_rating.infrastructure.sync_worker import (
    lock_key,
    should_poll,
)
from app.modules.capabilities.admission_rating.presentation.router import router
from app.modules.maintenance.presentation.dependencies import (
    enforce_user_access_available,
    enforce_user_write_available,
)
from app.modules.tenancy.presentation.dependencies import require_tenant_access


def valid_config() -> dict:
    return {
        "provider": "rut_admission",
        "admission_year": datetime.now(tz=UTC).year,
        "polling_interval_seconds": 900,
        "notifications_enabled": True,
        "title": "Место в рейтинге",
        "subtitle": "Введите код",
        "lookup_label": "Код поступающего",
        "not_found_text": "Не найдено",
    }


class InMemoryRatingRepository:
    def __init__(self) -> None:
        self.entries: dict[tuple[int, str], list[RatingEntry]] = {}
        self.subscriptions: dict[tuple[int, int, str], RatingSubscription] = {}

    def list_entries(self, bot_instance_id: int, code_hash: str):
        return self.entries.get((bot_instance_id, code_hash), [])

    def get_subscription(self, bot_instance_id: int, user_id: int, code_hash=None):
        values = [
            value
            for (bot, user, _), value in self.subscriptions.items()
            if bot == bot_instance_id and user == user_id
        ]
        if code_hash is not None:
            return self.subscriptions.get((bot_instance_id, user_id, code_hash))
        return values[-1] if values else None

    def save_subscription(self, value: RatingSubscription):
        stored = replace(value, id=value.id or len(self.subscriptions) + 1)
        self.subscriptions[(stored.bot_instance_id, stored.user_id, stored.applicant_code_hash)] = stored
        return stored


def test_config_is_strict_bounded_and_rejects_markup() -> None:
    assert validate_admission_rating_config(valid_config())["provider"] == "rut_admission"
    with pytest.raises(InvalidAdmissionRatingConfig):
        validate_admission_rating_config({**valid_config(), "provider_url": "https://evil.test"})
    with pytest.raises(InvalidAdmissionRatingConfig):
        validate_admission_rating_config({**valid_config(), "title": "<b>unsafe</b>"})
    with pytest.raises(InvalidAdmissionRatingConfig):
        validate_admission_rating_config({**valid_config(), "polling_interval_seconds": 5})


def test_lookup_and_subscription_are_tenant_scoped() -> None:
    repository = InMemoryRatingRepository()
    code = normalize_applicant_code(" ab 12 ")
    bot_one_hash = applicant_code_hash(1, code)
    bot_two_hash = applicant_code_hash(2, code)
    assert bot_one_hash != bot_two_hash
    repository.entries[(1, bot_one_hash)] = [
        RatingEntry(
            10, code, "ИТ", "бакалавр", 250, "1", "CONCOURSE", "Основная", 4, 20, datetime.now(tz=UTC)
        )
    ]
    assert (
        len(
            LookupAdmissionRating(repository)
            .execute(bot_instance_id=1, user_id=7, applicant_code="ab 12")
            .entries
        )
        == 1
    )
    assert (
        LookupAdmissionRating(repository)
        .execute(bot_instance_id=2, user_id=7, applicant_code="ab 12")
        .entries
        == []
    )

    saved = SetAdmissionRatingSubscription(repository).execute(
        bot_instance_id=1, installation_id=11, user_id=7, applicant_code="ab 12", active=True
    )
    assert saved.is_active
    assert (
        not LookupAdmissionRating(repository)
        .execute(bot_instance_id=2, user_id=7, applicant_code="ab 12")
        .is_subscribed
    )


def test_worker_policy_is_idempotent_and_lock_is_per_installation() -> None:
    assert lock_key(10) != lock_key(11)
    assert rating_change_notification_payload(10) == {"installation_id": 10}
    now = datetime.now(tz=UTC)
    assert should_poll(None, 900, now)
    assert not should_poll(now, 900, now)
    assert not has_meaningful_rating_change(
        old_position=4,
        new_position=4,
        old_group="Основная 12.08.2026",
        new_group="Основная 13.08.2026",
        available_places=20,
    )


class ProviderResponse:
    def __init__(self, content: bytes = b"{}") -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass

    def json(self):
        return {}


class RetryingClient:
    def __init__(self) -> None:
        self.calls = 0

    async def get(self, _path, *, params):
        self.calls += 1
        if self.calls == 1:
            raise httpx.ConnectError("temporary")
        return ProviderResponse()


@pytest.mark.asyncio
async def test_provider_retries_and_enforces_response_bound(monkeypatch) -> None:
    async def no_sleep(_delay):
        return None

    monkeypatch.setattr(provider_module.asyncio, "sleep", no_sleep)
    client = RetryingClient()
    assert await RutAdmissionProvider()._get_json(client, "/rating", {}) == {}
    assert client.calls == 2

    monkeypatch.setattr(provider_module, "_MAX_RESPONSE_BYTES", 1)

    class OversizedClient:
        async def get(self, _path, *, params):
            return ProviderResponse(b"{}")

    with pytest.raises(RutAdmissionProviderError):
        await RutAdmissionProvider()._get_json(OversizedClient(), "/rating", {})


def test_provider_parser_projects_plans_and_deduplicates_applicants() -> None:
    plans = parse_plans(
        {
            "result": [
                {
                    "concourseGroups": [
                        {
                            "planReceptionUrl": "/plan/42",
                            "specDisplayName": "Информатика",
                            "specQualifier": "бакалавр",
                            "planNumbers": {
                                "integers": {
                                    "ALL": {"PLAN": 30},
                                    "CONCOURSE": {"PLAN": 20},
                                }
                            },
                        }
                    ]
                }
            ]
        }
    )
    assert plans[0].plan_id == 42
    assert plans[0].totals["CONCOURSE"] == 20

    ratings = parse_ratings(
        {
            "competitions": [
                {
                    "competitionName": "Общий конкурс",
                    "projectEntrantGroups": [
                        {
                            "name": "Основная",
                            "entrants": [
                                {
                                    "displayName": "AB12",
                                    "points": "250,5",
                                    "preferenceIndexDisplay": "1",
                                    "ratingIndex": 4,
                                }
                            ],
                        }
                    ],
                    "concourseEntrantGroups": [
                        {
                            "name": "Дубликат",
                            "entrants": [
                                {
                                    "displayName": "AB12",
                                    "points": 250.5,
                                    "preferenceIndexDisplay": "1",
                                    "ratingIndex": 4,
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )
    assert len(ratings) == 1
    assert ratings[0].points == 250.5
    assert ratings[0].competition == "CONCOURSE"
    assert has_meaningful_rating_change(
        old_position=5,
        new_position=4,
        old_group="Основная",
        new_group="Основная",
        available_places=20,
    )
    assert not has_meaningful_rating_change(
        old_position=25,
        new_position=24,
        old_group="Основная",
        new_group="Основная",
        available_places=20,
    )


class DummySession:
    pass


def _principal(bot_id: int) -> CurrentPrincipal:
    return CurrentPrincipal("u:7", "student", "max", 7, None, bot_id, f"bot-{bot_id}")


def test_http_rejects_user_token_bound_to_another_bot() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/capabilities/admission-rating")
    selected_bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    principal = _principal(1)
    app.dependency_overrides[require_tenant_access] = lambda: require_tenant_access(
        bot=selected_bot, principal=principal, db=None
    )
    app.dependency_overrides[get_db] = lambda: DummySession()

    response = TestClient(app).get("/capabilities/admission-rating/lookup?applicant_code=ABC")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_mismatch"


def test_subscription_payload_rejects_personal_or_free_form_fields() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/capabilities/admission-rating")
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app.dependency_overrides[require_student] = lambda: _principal(1)
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[enforce_user_write_available] = lambda: None
    app.dependency_overrides[get_db] = lambda: DummySession()

    response = TestClient(app).post(
        "/capabilities/admission-rating/subscribe",
        json={"applicant_code": "ABC", "full_name": "Иван Иванов"},
    )

    assert response.status_code == 422


def test_full_stop_dependency_blocks_lookup() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/capabilities/admission-rating")

    def blocked() -> None:
        raise service_unavailable("Технические работы", code="maintenance_mode", mode="full_stop")

    app.dependency_overrides[enforce_user_access_available] = blocked
    response = TestClient(app).get("/capabilities/admission-rating/lookup?applicant_code=ABC")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "maintenance_mode"
