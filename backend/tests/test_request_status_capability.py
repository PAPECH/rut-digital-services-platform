import json

import pytest

from app.modules.capabilities.request_status.application.use_cases import (
    LookupRequestStatus,
    SetRequestStatusSubscription,
)
from app.modules.capabilities.request_status.domain.config import parse_request_status_config
from app.modules.capabilities.request_status.domain.identity import (
    normalize_request_number,
    request_number_hash,
)
from app.modules.capabilities.request_status.infrastructure import provider as provider_module
from app.modules.capabilities.request_status.infrastructure.provider import parse_status_rows
from tests.test_capability_registry import valid_config


class Repository:
    def __init__(self) -> None:
        self.states = {}
        self.subscriptions = {}

    def get_state(self, bot_instance_id, number_hash):
        return self.states.get((bot_instance_id, number_hash))

    def upsert_states(self, states):
        for state in states:
            self.states[(state.bot_instance_id, state.request_number_hash)] = state

    def get_subscription(self, bot_instance_id, user_id, number_hash=None):
        if number_hash is not None:
            return self.subscriptions.get((bot_instance_id, user_id, number_hash))
        return next(
            (
                subscription
                for (tenant, owner, _), subscription in self.subscriptions.items()
                if tenant == bot_instance_id and owner == user_id
            ),
            None,
        )

    def save_subscription(self, subscription):
        self.subscriptions[
            (
                subscription.bot_instance_id,
                subscription.user_id,
                subscription.request_number_hash,
            )
        ] = subscription
        return subscription


class Provider:
    def __init__(self, values):
        self.values = values
        self.calls = 0

    def read_statuses(self, config):
        self.calls += 1
        return self.values


class StreamingResponse:
    status_code = 200

    def __init__(self, payload: object) -> None:
        self.content = json.dumps(payload).encode()
        self.closed = False

    def iter_content(self, *, chunk_size: int):
        yield from (
            self.content[offset : offset + chunk_size] for offset in range(0, len(self.content), chunk_size)
        )

    def close(self) -> None:
        self.closed = True


def test_normalization_hashes_are_stable_and_tenant_specific() -> None:
    assert normalize_request_number(" ab 12 ", "compact") == "AB12"
    assert request_number_hash(1, "AB12") == request_number_hash(1, "AB12")
    assert request_number_hash(1, "AB12") != request_number_hash(2, "AB12")


def test_provider_rows_use_configured_columns_and_bounds() -> None:
    assert parse_status_rows(
        [["ignored", " 12 ", "Готово"], ["short"]],
        number_column=1,
        status_column=2,
        normalization="trim",
    ) == {"12": "Готово"}


def test_provider_response_is_streamed_bounded_and_closed(monkeypatch) -> None:
    response = StreamingResponse({"values": [["12", "Готово"]]})
    assert provider_module._read_values_response(response) == [["12", "Готово"]]
    assert response.closed

    monkeypatch.setattr(provider_module, "_MAX_RESPONSE_BYTES", 8)
    oversized = StreamingResponse({"values": [["12", "Готово"]]})
    with pytest.raises(ValueError, match="size limit"):
        provider_module._read_values_response(oversized)
    assert oversized.closed


def test_provider_rejects_oversized_cells() -> None:
    with pytest.raises(ValueError, match="oversized cell"):
        parse_status_rows(
            [["12", "x" * 2_001]],
            number_column=0,
            status_column=1,
            normalization="trim",
        )


def test_lookup_and_subscription_do_not_cross_tenants() -> None:
    repository = Repository()
    provider = Provider({"ABC": "Готово"})
    config = parse_request_status_config({**valid_config(), "normalization": "compact"})
    result = LookupRequestStatus(repository, provider).execute(
        bot_instance_id=1,
        installation_id=4,
        user_id=7,
        request_number=" a b c ",
        config=config,
    )
    assert result.status == "Готово"
    assert provider.calls == 1
    SetRequestStatusSubscription(repository).execute(
        bot_instance_id=1,
        installation_id=4,
        user_id=7,
        request_number="ABC",
        config=config,
        active=True,
    )
    other = LookupRequestStatus(repository, Provider({"ABC": "Другое"})).execute(
        bot_instance_id=2,
        installation_id=8,
        user_id=7,
        request_number="ABC",
        config=config,
    )
    assert not other.is_subscribed
    assert len(repository.states) == 2
