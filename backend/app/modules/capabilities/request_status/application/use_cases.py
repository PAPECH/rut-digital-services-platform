from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from ..domain.config import RequestStatusConfig
from ..domain.entities import RequestStatusState, RequestStatusSubscription
from ..domain.identity import normalize_request_number, request_number_hash
from ..domain.repositories import RequestStatusRepository
from .ports import RequestStatusProvider


class RequestStatusProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RequestStatusLookupResult:
    request_number: str
    status: str | None
    checked_at: datetime | None
    is_subscribed: bool


class LookupRequestStatus:
    def __init__(
        self,
        repository: RequestStatusRepository,
        provider: RequestStatusProvider,
    ) -> None:
        self._repository = repository
        self._provider = provider

    def execute(
        self,
        *,
        bot_instance_id: int,
        installation_id: int,
        user_id: int,
        request_number: str,
        config: RequestStatusConfig,
    ) -> RequestStatusLookupResult:
        normalized = normalize_request_number(request_number, config.normalization)
        number_hash = request_number_hash(bot_instance_id, normalized)
        state = self._repository.get_state(bot_instance_id, number_hash)
        if state is None:
            try:
                statuses = self._provider.read_statuses(config)
            except Exception as exc:
                raise RequestStatusProviderUnavailable from exc
            now = datetime.now(tz=UTC)
            state = RequestStatusState(
                id=None,
                bot_instance_id=bot_instance_id,
                installation_id=installation_id,
                request_number=normalized,
                request_number_hash=number_hash,
                last_status=statuses.get(normalized),
                checked_at=now,
            )
            self._repository.upsert_states([state])
        subscription = self._repository.get_subscription(
            bot_instance_id,
            user_id,
            number_hash,
        )
        return RequestStatusLookupResult(
            request_number=normalized,
            status=state.last_status,
            checked_at=state.checked_at,
            is_subscribed=bool(subscription and subscription.is_active),
        )


class GetRequestStatusSubscription:
    def __init__(self, repository: RequestStatusRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, user_id: int) -> RequestStatusSubscription | None:
        subscription = self._repository.get_subscription(bot_instance_id, user_id)
        return subscription if subscription and subscription.is_active else None


class SetRequestStatusSubscription:
    def __init__(self, repository: RequestStatusRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        bot_instance_id: int,
        installation_id: int,
        user_id: int,
        request_number: str,
        config: RequestStatusConfig,
        active: bool,
    ) -> RequestStatusSubscription:
        normalized = normalize_request_number(request_number, config.normalization)
        number_hash = request_number_hash(bot_instance_id, normalized)
        current = self._repository.get_subscription(bot_instance_id, user_id, number_hash)
        if current is None:
            current = RequestStatusSubscription(
                id=None,
                bot_instance_id=bot_instance_id,
                installation_id=installation_id,
                user_id=user_id,
                request_number=normalized,
                request_number_hash=number_hash,
                is_active=active,
            )
        else:
            current = replace(current, is_active=active)
        return self._repository.save_subscription(current)
