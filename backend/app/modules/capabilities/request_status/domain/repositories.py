from typing import Protocol

from .entities import RequestStatusState, RequestStatusSubscription


class RequestStatusRepository(Protocol):
    def get_state(self, bot_instance_id: int, number_hash: str) -> RequestStatusState | None: ...

    def upsert_states(self, states: list[RequestStatusState]) -> None: ...

    def get_subscription(
        self,
        bot_instance_id: int,
        user_id: int,
        number_hash: str | None = None,
    ) -> RequestStatusSubscription | None: ...

    def save_subscription(
        self,
        subscription: RequestStatusSubscription,
    ) -> RequestStatusSubscription: ...
