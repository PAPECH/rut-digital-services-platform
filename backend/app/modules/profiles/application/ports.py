from __future__ import annotations

from typing import Any, Protocol

from ..domain.entities import BotMembership, SharedProfile


class ProfileGateway(Protocol):
    def get_shared_profile(self, user_id: int) -> SharedProfile | None: ...

    def update_shared_profile(self, user_id: int, values: dict[str, Any]) -> SharedProfile: ...

    def get_membership(self, bot_instance_id: int, user_id: int) -> BotMembership | None: ...

    def create_membership(self, membership: BotMembership) -> BotMembership: ...

    def update_membership_data(
        self,
        bot_instance_id: int,
        user_id: int,
        values: dict[str, Any],
    ) -> BotMembership: ...

    def set_membership_campaign_source(
        self,
        bot_instance_id: int,
        user_id: int,
        campaign_link_id: int,
    ) -> None:
        """First-touch only: no-op if the membership already has a source recorded."""
        ...
