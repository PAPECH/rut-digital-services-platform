from __future__ import annotations

from dataclasses import replace

from ..domain.entities import (
    CapabilityDescriptor,
    CapabilityInstallation,
    CapabilityRegistry,
    UnknownCapability,
)
from ..domain.repositories import CapabilityInstallationRepository
from .commands import ConfigureCapabilityCommand, SetCapabilityEnabledCommand


class CapabilityNotInstalled(RuntimeError):
    pass


class CapabilityDisabled(RuntimeError):
    pass


class CapabilityConfigRevisionConflict(RuntimeError):
    pass


class CapabilityConfigurationRequired(RuntimeError):
    pass


class ListCapabilityCatalog:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def execute(self) -> tuple[CapabilityDescriptor, ...]:
        return self._registry.list()


class ListCapabilityInstallations:
    def __init__(self, repository: CapabilityInstallationRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[CapabilityInstallation]:
        return self._repository.list_for_bot(bot_instance_id)


def bot_has_profile_gated_capability(
    repository: CapabilityInstallationRepository,
    registry: CapabilityRegistry,
    bot_instance_id: int,
) -> bool:
    """True if bot_instance_id has any *enabled* capability installation with a view that
    requires_complete_profile — backs Task 054's profile-tab toggle validation (a bot cannot
    disable its profile tab while a capability it has turned on still needs one)."""
    for installation in repository.list_for_bot(bot_instance_id):
        if not installation.is_enabled:
            continue
        try:
            descriptor = registry.get(installation.capability_key)
        except UnknownCapability:
            continue
        if any(view.requires_complete_profile for view in descriptor.views):
            return True
    return False


class GetEnabledCapability:
    def __init__(
        self,
        repository: CapabilityInstallationRepository,
        registry: CapabilityRegistry,
    ) -> None:
        self._repository = repository
        self._registry = registry

    def execute(
        self,
        bot_instance_id: int,
        capability_key: str,
    ) -> tuple[CapabilityInstallation, CapabilityDescriptor]:
        descriptor = self._registry.get(capability_key)
        installation = self._repository.get(bot_instance_id, capability_key)
        if installation is None:
            raise CapabilityNotInstalled(capability_key)
        if not installation.is_enabled:
            raise CapabilityDisabled(capability_key)
        descriptor.validate_config(installation.config)
        return installation, descriptor


class ConfigureCapability:
    def __init__(
        self,
        repository: CapabilityInstallationRepository,
        registry: CapabilityRegistry,
    ) -> None:
        self._repository = repository
        self._registry = registry

    def execute(self, command: ConfigureCapabilityCommand) -> CapabilityInstallation:
        descriptor = self._registry.get(command.capability_key)
        normalized = descriptor.validate_config(command.config)
        current = self._repository.get(command.bot_instance_id, command.capability_key)
        if current is None:
            if not command.create_if_missing:
                raise CapabilityNotInstalled(command.capability_key)
            current = self._repository.create(
                CapabilityInstallation(
                    id=None,
                    bot_instance_id=command.bot_instance_id,
                    capability_key=command.capability_key,
                )
            )
        if command.require_enabled and not current.is_enabled:
            raise CapabilityDisabled(command.capability_key)
        if current.config_revision != command.expected_revision:
            raise CapabilityConfigRevisionConflict(command.capability_key)
        updated = replace(
            current,
            config=normalized,
            config_revision=current.config_revision + 1,
            configured_by=command.configured_by,
            last_health_status="unknown",
            last_health_at=None,
            last_health_error_code=None,
        )
        return self._repository.save(updated, expected_revision=current.config_revision)


class SetCapabilityEnabled:
    def __init__(
        self,
        repository: CapabilityInstallationRepository,
        registry: CapabilityRegistry,
    ) -> None:
        self._repository = repository
        self._registry = registry

    def execute(self, command: SetCapabilityEnabledCommand) -> CapabilityInstallation:
        descriptor = self._registry.get(command.capability_key)
        current = self._repository.get(command.bot_instance_id, command.capability_key)
        if current is None:
            raise CapabilityNotInstalled(command.capability_key)
        if command.enabled:
            if not current.config:
                raise CapabilityConfigurationRequired(command.capability_key)
            descriptor.validate_config(current.config)
        return self._repository.save(
            replace(
                current,
                is_enabled=command.enabled,
                enabled_by=command.changed_by,
            )
        )


class ReorderCapabilityInstallations:
    def __init__(self, repository: CapabilityInstallationRepository) -> None:
        self._repository = repository

    def execute(
        self,
        bot_instance_id: int,
        capability_keys: list[str],
    ) -> list[CapabilityInstallation]:
        if len(capability_keys) != len(set(capability_keys)):
            raise ValueError("Capability order contains duplicates")
        return self._repository.reorder(bot_instance_id, capability_keys)
