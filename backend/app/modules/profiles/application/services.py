from __future__ import annotations

from ..domain.entities import BotMembership, SharedProfile
from .ports import ProfileGateway


class GetSharedProfile:
    def __init__(self, gateway: ProfileGateway) -> None:
        self._gateway = gateway

    def execute(self, user_id: int) -> SharedProfile | None:
        return self._gateway.get_shared_profile(user_id)


class EnsureBotMembership:
    def __init__(self, gateway: ProfileGateway) -> None:
        self._gateway = gateway

    def execute(self, bot_instance_id: int, user_id: int) -> BotMembership:
        current = self._gateway.get_membership(bot_instance_id, user_id)
        if current is not None:
            return current
        return self._gateway.create_membership(
            BotMembership(id=None, bot_instance_id=bot_instance_id, user_id=user_id)
        )
