from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from ..domain.entities import BotInstance
from ..domain.profile_consistency import profile_disabled_with_required_fields
from ..domain.repositories import BotInstanceRepository
from .commands import CreateBotInstanceCommand, UpdateBotInstanceCommand


class BotSlugAlreadyExists(RuntimeError):
    pass


class BotInstanceNotFound(RuntimeError):
    pass


class ProfileDisabledWithRequiredFields(RuntimeError):
    """Task 054: profile.enabled=false cannot coexist with a required profile_schema field."""


class ProfileDisabledWithGatedCapability(RuntimeError):
    """Task 054: profile.enabled=false cannot coexist with an enabled capability whose view
    requires a complete profile."""


class CreateBotInstance:
    def __init__(self, repository: BotInstanceRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateBotInstanceCommand) -> BotInstance:
        if self._repository.get_by_slug(command.slug.strip().lower()) is not None:
            raise BotSlugAlreadyExists(command.slug)
        if profile_disabled_with_required_fields(command.settings, command.profile_schema):
            raise ProfileDisabledWithRequiredFields(command.slug)
        return self._repository.add(
            BotInstance(
                id=None,
                slug=command.slug,
                name=command.name,
                description=command.description,
                is_active=command.is_active,
                order=command.order,
                branding=command.branding,
                settings=command.settings,
                profile_schema=command.profile_schema,
            )
        )


class ListBotInstances:
    def __init__(self, repository: BotInstanceRepository) -> None:
        self._repository = repository

    def execute(self, *, include_deleted: bool = False) -> list[BotInstance]:
        return self._repository.list_all(include_deleted=include_deleted)


class UpdateBotInstance:
    def __init__(
        self,
        repository: BotInstanceRepository,
        *,
        has_profile_gated_capability: Callable[[int], bool] | None = None,
    ) -> None:
        self._repository = repository
        # Optional injected check against another module's data (capabilities) — kept as a
        # plain callable rather than a new cross-module port; defaults to "never gated" for
        # any caller that doesn't pass one (e.g. callers that don't touch profile.enabled).
        self._has_profile_gated_capability = has_profile_gated_capability or (lambda _bot_id: False)

    def execute(self, command: UpdateBotInstanceCommand) -> BotInstance:
        current = self._repository.get(command.bot_id)
        if current is None or current.is_deleted:
            raise BotInstanceNotFound(str(command.bot_id))
        changes = {
            key: value
            for key, value in {
                "name": command.name,
                "description": command.description,
                "is_active": command.is_active,
                "order": command.order,
                "branding": command.branding,
                "settings": command.settings,
                "profile_schema": command.profile_schema,
            }.items()
            if value is not None
        }
        updated = replace(current, **changes)
        if profile_disabled_with_required_fields(updated.settings, updated.profile_schema):
            raise ProfileDisabledWithRequiredFields(str(command.bot_id))
        profile_enabled = (updated.settings.get("profile") or {}).get("enabled", True)
        if not profile_enabled and self._has_profile_gated_capability(command.bot_id):
            raise ProfileDisabledWithGatedCapability(str(command.bot_id))
        return self._repository.update(updated)


class DeleteBotInstance:
    """Soft-delete: hides the bot and stops its process, keeping all data for restore."""

    def __init__(self, repository: BotInstanceRepository) -> None:
        self._repository = repository

    def execute(self, bot_id: int) -> BotInstance:
        if self._repository.get(bot_id) is None:
            raise BotInstanceNotFound(str(bot_id))
        return self._repository.soft_delete(bot_id)


class RestoreBotInstance:
    def __init__(self, repository: BotInstanceRepository) -> None:
        self._repository = repository

    def execute(self, bot_id: int) -> BotInstance:
        current = self._repository.get(bot_id)
        if current is None:
            raise BotInstanceNotFound(str(bot_id))
        conflict = self._repository.get_by_slug(current.slug)
        if conflict is not None and conflict.id != bot_id:
            raise BotSlugAlreadyExists(current.slug)
        return self._repository.restore(bot_id)
