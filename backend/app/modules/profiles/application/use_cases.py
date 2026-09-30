from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..domain.fields import (
    DIRECT_OPTIONAL_PROFILE_KEYS,
    InvalidProfileField,
    ProfileFieldDefinition,
)
from .dto import BotProfile, UpdateBotProfileCommand
from .ports import ProfileGateway
from .services import EnsureBotMembership


class ProfileNotFound(LookupError):
    pass


class ProfileFieldNotConfigured(ValueError):
    pass


class GetBotProfile:
    def __init__(self, gateway: ProfileGateway) -> None:
        self._gateway = gateway

    def execute(self, bot_instance_id: int, user_id: int) -> BotProfile:
        profile = self._gateway.get_shared_profile(user_id)
        if profile is None:
            raise ProfileNotFound(user_id)
        membership = EnsureBotMembership(self._gateway).execute(bot_instance_id, user_id)
        return BotProfile(shared=profile, membership=membership)


class UpdateBotProfile:
    def __init__(self, gateway: ProfileGateway) -> None:
        self._gateway = gateway

    def execute(
        self,
        bot_instance_id: int,
        user_id: int,
        schema: Iterable[Mapping[str, Any]],
        command: UpdateBotProfileCommand,
    ) -> BotProfile:
        GetBotProfile(self._gateway).execute(bot_instance_id, user_id)
        fields: dict[str, ProfileFieldDefinition] = {}
        for raw_field in schema:
            try:
                field = ProfileFieldDefinition.from_mapping(raw_field)
            except InvalidProfileField:
                continue
            fields[field.key] = field
        unknown = set(command.custom_data) - set(fields)
        if unknown:
            raise ProfileFieldNotConfigured(sorted(unknown)[0])

        shared_values = {
            "first_name": command.first_name,
            "last_name": command.last_name,
            "patronymic": command.patronymic,
            "email": command.email,
            "birth_date": command.birth_date,
        }
        local_values: dict[str, Any] = {}
        for key, value in command.custom_data.items():
            normalized = fields[key].normalize(value)
            if key in DIRECT_OPTIONAL_PROFILE_KEYS:
                shared_values[key] = normalized
            else:
                local_values[key] = normalized

        self._gateway.update_shared_profile(user_id, shared_values)
        if local_values:
            self._gateway.update_membership_data(bot_instance_id, user_id, local_values)
        return GetBotProfile(self._gateway).execute(bot_instance_id, user_id)
