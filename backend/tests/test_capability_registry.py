from dataclasses import replace

import pytest

from app.modules.capabilities.application.commands import (
    ConfigureCapabilityCommand,
    SetCapabilityEnabledCommand,
)
from app.modules.capabilities.application.use_cases import (
    CapabilityConfigRevisionConflict,
    CapabilityConfigurationRequired,
    CapabilityDisabled,
    CapabilityNotInstalled,
    ConfigureCapability,
    GetEnabledCapability,
    SetCapabilityEnabled,
)
from app.modules.capabilities.domain.entities import (
    CapabilityDescriptor,
    CapabilityInstallation,
    CapabilityRegistry,
    CapabilityView,
    InvalidCapability,
)
from app.modules.capabilities.infrastructure.catalog import capability_registry
from app.modules.capabilities.request_status.domain.config import (
    InvalidRequestStatusConfig,
    validate_request_status_config,
)


def valid_config() -> dict:
    return {
        "provider": "google_sheets",
        "credential_ref": "mock",
        "spreadsheet_id": "mock",
        "sheet_range": "B:C",
        "request_number_column": 0,
        "status_column": 1,
        "normalization": "trim",
        "polling_interval_seconds": 300,
        "notifications_enabled": True,
        "title": "Проверить статус",
        "subtitle": "Введите номер заявления",
        "lookup_label": "Номер",
        "not_found_text": "Не найдено",
    }


class InMemoryInstallationRepository:
    def __init__(self) -> None:
        self.items: dict[tuple[int, str], CapabilityInstallation] = {}
        self.next_id = 1

    def list_for_bot(self, bot_instance_id: int):
        return [item for item in self.items.values() if item.bot_instance_id == bot_instance_id]

    def get(self, bot_instance_id: int, capability_key: str):
        return self.items.get((bot_instance_id, capability_key))

    def create(self, installation: CapabilityInstallation):
        stored = replace(installation, id=self.next_id)
        self.next_id += 1
        self.items[(stored.bot_instance_id, stored.capability_key)] = stored
        return stored

    def save(self, installation: CapabilityInstallation, *, expected_revision=None):
        current = self.get(installation.bot_instance_id, installation.capability_key)
        if expected_revision is not None and (
            current is None or current.config_revision != expected_revision
        ):
            raise CapabilityConfigRevisionConflict
        self.items[(installation.bot_instance_id, installation.capability_key)] = installation
        return installation

    def reorder(self, bot_instance_id: int, capability_keys: list[str]):
        return []


def test_registry_rejects_duplicate_keys_and_unknown_views() -> None:
    descriptor = CapabilityDescriptor(
        key="sample_capability",
        version="1.2.3",
        name="Sample",
        description="Sample capability",
        admin_editor_key="sample_capability",
        views=(CapabilityView("main", "Main", None, "box"),),
        validate_config=lambda config: config,
        public_config=lambda config: {},
    )
    with pytest.raises(InvalidCapability):
        CapabilityRegistry((descriptor, descriptor))
    with pytest.raises(LookupError):
        descriptor.get_view("missing")


def test_request_status_config_is_strict_and_rejects_markup() -> None:
    assert validate_request_status_config(valid_config())["provider"] == "google_sheets"
    with pytest.raises(InvalidRequestStatusConfig):
        validate_request_status_config({**valid_config(), "unexpected": True})
    with pytest.raises(InvalidRequestStatusConfig):
        validate_request_status_config({**valid_config(), "title": "<b>Unsafe</b>"})
    with pytest.raises(InvalidRequestStatusConfig):
        validate_request_status_config({**valid_config(), "credential_ref": "../../service-account.json"})


def test_configuration_revision_enablement_and_tenant_scope() -> None:
    repository = InMemoryInstallationRepository()
    configure = ConfigureCapability(repository, capability_registry)
    first = configure.execute(
        ConfigureCapabilityCommand(
            bot_instance_id=1,
            capability_key="request_status",
            config=valid_config(),
            expected_revision=0,
            configured_by=10,
            create_if_missing=True,
        )
    )
    assert first.config_revision == 1
    with pytest.raises(CapabilityConfigRevisionConflict):
        configure.execute(
            ConfigureCapabilityCommand(
                bot_instance_id=1,
                capability_key="request_status",
                config=valid_config(),
                expected_revision=0,
                configured_by=10,
            )
        )
    enabled = SetCapabilityEnabled(repository, capability_registry).execute(
        SetCapabilityEnabledCommand(
            bot_instance_id=1,
            capability_key="request_status",
            enabled=True,
            changed_by=10,
        )
    )
    assert enabled.is_enabled
    assert (
        GetEnabledCapability(repository, capability_registry).execute(1, "request_status")[0].id == enabled.id
    )
    with pytest.raises(CapabilityNotInstalled):
        GetEnabledCapability(repository, capability_registry).execute(2, "request_status")


def test_bot_manager_cannot_install_missing_capability_by_configuring_it() -> None:
    repository = InMemoryInstallationRepository()

    with pytest.raises(CapabilityNotInstalled):
        ConfigureCapability(repository, capability_registry).execute(
            ConfigureCapabilityCommand(
                bot_instance_id=1,
                capability_key="request_status",
                config=valid_config(),
                expected_revision=0,
                configured_by=10,
            )
        )

    assert repository.get(1, "request_status") is None


def test_bot_manager_cannot_configure_disabled_capability() -> None:
    repository = InMemoryInstallationRepository()
    repository.create(
        CapabilityInstallation(
            id=None,
            bot_instance_id=1,
            capability_key="request_status",
        )
    )

    with pytest.raises(CapabilityDisabled):
        ConfigureCapability(repository, capability_registry).execute(
            ConfigureCapabilityCommand(
                bot_instance_id=1,
                capability_key="request_status",
                config=valid_config(),
                expected_revision=0,
                configured_by=10,
                require_enabled=True,
            )
        )


def test_unconfigured_or_disabled_capability_cannot_run() -> None:
    repository = InMemoryInstallationRepository()
    repository.create(
        CapabilityInstallation(
            id=None,
            bot_instance_id=1,
            capability_key="request_status",
        )
    )
    with pytest.raises(CapabilityDisabled):
        GetEnabledCapability(repository, capability_registry).execute(1, "request_status")
    with pytest.raises(CapabilityConfigurationRequired):
        SetCapabilityEnabled(repository, capability_registry).execute(
            SetCapabilityEnabledCommand(
                bot_instance_id=1,
                capability_key="request_status",
                enabled=True,
                changed_by=10,
            )
        )
