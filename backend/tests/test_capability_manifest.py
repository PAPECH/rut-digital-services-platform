from importlib import import_module

from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.capabilities.domain.entities import CapabilityInstallation
from tests.test_capability_registry import valid_config

manifest_module = import_module("app.modules.maintenance.presentation.router")


class InstallationRepository:
    def __init__(self, _db) -> None:
        pass

    def list_for_bot(self, bot_instance_id: int) -> list[CapabilityInstallation]:
        return [
            CapabilityInstallation(
                id=1,
                bot_instance_id=bot_instance_id,
                capability_key="request_status",
                is_enabled=True,
                config=valid_config(),
                config_revision=1,
            ),
            CapabilityInstallation(
                id=2,
                bot_instance_id=bot_instance_id,
                capability_key="request_status",
                is_enabled=False,
                config=valid_config(),
                config_revision=1,
            ),
            CapabilityInstallation(
                id=3,
                bot_instance_id=bot_instance_id,
                capability_key="request_status",
                is_enabled=True,
                config={},
            ),
        ]


class MaintenanceRepository:
    def __init__(self, _db) -> None:
        pass

    def get(self, _scope_key: str):
        return None


def test_manifest_exposes_only_enabled_valid_capabilities_without_private_config(monkeypatch) -> None:
    monkeypatch.setattr(
        manifest_module,
        "SqlAlchemyCapabilityInstallationRepository",
        InstallationRepository,
    )
    monkeypatch.setattr(
        manifest_module,
        "SqlAlchemyMaintenanceRepository",
        MaintenanceRepository,
    )

    manifest = manifest_module.get_manifest(
        BotInstance(
            id=7,
            slug="bot-7",
            name="Седьмой бот",
            settings={
                "bottom_navigation": {
                    "custom_items": [
                        {"category_slug": "contacts", "label": "Контакты", "icon": "contact"},
                    ],
                },
            },
        ),
        db=None,
    )

    assert len(manifest.capabilities) == 1
    public = manifest.capabilities[0]
    assert public.installation_id == 1
    assert public.key == "request_status"
    assert "credential_ref" not in public.public_config
    assert "spreadsheet_id" not in public.public_config
    assert manifest.bot.id == 7
    assert manifest.bot.settings.bottom_navigation.custom_items[0].category_slug == "contacts"
