from __future__ import annotations

from typing import Protocol

from ...profiles.domain.entities import SharedProfile


class ResultDeliveryGateway(Protocol):
    """Delivers a completed attempt's rendered result to the student. The one implementation
    in this task wraps the platform's existing push mechanism (`services.push.enqueue_push`)
    and splits the text across the channel's message-length limit -- see
    `infrastructure.push_delivery`."""

    def deliver_result(self, *, bot_instance_id: int, user_id: int, text: str) -> None: ...


class ProfileReader(Protocol):
    """The one shared-profile read `CompleteAttempt` needs to freeze identity fields onto a
    completed attempt (Task 080) -- deliberately narrower than
    `profiles.application.ports.ProfileGateway`, which also covers membership writes this module
    never needs. `SqlAlchemyProfileGateway` (from `modules.profiles.infrastructure.gateways`)
    already satisfies this structurally; no adapter is written for it."""

    def get_shared_profile(self, user_id: int) -> SharedProfile | None: ...
