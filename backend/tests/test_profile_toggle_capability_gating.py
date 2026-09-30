"""Task 054 (configurable profile tab) — the capability-gating half of the bidirectional
validation: a bot cannot disable its profile tab while an enabled capability still needs a
complete profile, and symmetrically cannot enable such a capability while the tab is off.
"""

from __future__ import annotations

import pytest

from app.core.errors import ApiError
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.capabilities.application.use_cases import bot_has_profile_gated_capability
from app.modules.capabilities.domain.entities import (
    CapabilityDescriptor,
    CapabilityInstallation,
    CapabilityRegistry,
    CapabilityView,
)
from app.modules.capabilities.presentation.router import (
    _reject_if_capability_needs_profile_but_it_is_disabled,
)


class _FakeInstallationRepository:
    def __init__(self, installations: list[CapabilityInstallation]) -> None:
        self._installations = installations

    def list_for_bot(self, bot_instance_id: int) -> list[CapabilityInstallation]:
        return [i for i in self._installations if i.bot_instance_id == bot_instance_id]


def _gated_descriptor(key: str = "gated_capability") -> CapabilityDescriptor:
    return CapabilityDescriptor(
        key=key,
        version="1.0.0",
        name="Gated",
        description="Needs a complete profile",
        admin_editor_key=key,
        views=(CapabilityView("main", "Main", None, "box", requires_complete_profile=True),),
        validate_config=lambda config: config,
        public_config=lambda config: {},
    )


def _ungated_descriptor(key: str = "plain_capability") -> CapabilityDescriptor:
    return CapabilityDescriptor(
        key=key,
        version="1.0.0",
        name="Plain",
        description="No profile requirement",
        admin_editor_key=key,
        views=(CapabilityView("main", "Main", None, "box"),),
        validate_config=lambda config: config,
        public_config=lambda config: {},
    )


def test_bot_has_profile_gated_capability_true_only_when_enabled_and_gated() -> None:
    registry = CapabilityRegistry((_gated_descriptor(), _ungated_descriptor()))

    enabled_gated = CapabilityInstallation(
        id=1, bot_instance_id=1, capability_key="gated_capability", is_enabled=True
    )
    assert bot_has_profile_gated_capability(
        _FakeInstallationRepository([enabled_gated]), registry, 1
    )

    disabled_gated = CapabilityInstallation(
        id=2, bot_instance_id=1, capability_key="gated_capability", is_enabled=False
    )
    assert not bot_has_profile_gated_capability(
        _FakeInstallationRepository([disabled_gated]), registry, 1
    )

    enabled_plain = CapabilityInstallation(
        id=3, bot_instance_id=1, capability_key="plain_capability", is_enabled=True
    )
    assert not bot_has_profile_gated_capability(
        _FakeInstallationRepository([enabled_plain]), registry, 1
    )

    # A different bot's installation must never count.
    assert not bot_has_profile_gated_capability(
        _FakeInstallationRepository([enabled_gated]), registry, 2
    )


def test_bot_has_profile_gated_capability_ignores_an_unregistered_capability_key() -> None:
    # A stale installation row for a capability that's since been removed from the
    # deployment-installed registry must not crash the check.
    registry = CapabilityRegistry((_ungated_descriptor(),))
    stale = CapabilityInstallation(
        id=1, bot_instance_id=1, capability_key="removed_capability", is_enabled=True
    )
    assert not bot_has_profile_gated_capability(_FakeInstallationRepository([stale]), registry, 1)


def test_reject_if_capability_needs_profile_but_it_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.capabilities.presentation.router as router_module

    monkeypatch.setattr(
        router_module, "capability_registry", CapabilityRegistry((_gated_descriptor(),))
    )
    bot_with_profile_off = BotInstance(
        id=1, slug="bot-1", name="Bot", settings={"profile": {"enabled": False}}
    )
    with pytest.raises(ApiError) as exc_info:
        _reject_if_capability_needs_profile_but_it_is_disabled(
            bot_with_profile_off, "gated_capability"
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "capability_requires_profile_enabled"


def test_reject_if_capability_needs_profile_allows_when_profile_is_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.modules.capabilities.presentation.router as router_module

    monkeypatch.setattr(
        router_module, "capability_registry", CapabilityRegistry((_gated_descriptor(),))
    )
    bot_with_profile_on = BotInstance(id=1, slug="bot-1", name="Bot", settings={})
    _reject_if_capability_needs_profile_but_it_is_disabled(bot_with_profile_on, "gated_capability")


def test_reject_if_capability_needs_profile_allows_ungated_capability_regardless(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.modules.capabilities.presentation.router as router_module

    monkeypatch.setattr(
        router_module, "capability_registry", CapabilityRegistry((_ungated_descriptor(),))
    )
    bot_with_profile_off = BotInstance(
        id=1, slug="bot-1", name="Bot", settings={"profile": {"enabled": False}}
    )
    _reject_if_capability_needs_profile_but_it_is_disabled(
        bot_with_profile_off, "plain_capability"
    )
