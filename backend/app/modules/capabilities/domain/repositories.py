from typing import Protocol

from .entities import CapabilityInstallation


class CapabilityInstallationRepository(Protocol):
    def list_for_bot(self, bot_instance_id: int) -> list[CapabilityInstallation]: ...

    def get(self, bot_instance_id: int, capability_key: str) -> CapabilityInstallation | None: ...

    def create(self, installation: CapabilityInstallation) -> CapabilityInstallation: ...

    def save(
        self,
        installation: CapabilityInstallation,
        *,
        expected_revision: int | None = None,
    ) -> CapabilityInstallation: ...

    def reorder(
        self,
        bot_instance_id: int,
        capability_keys: list[str],
    ) -> list[CapabilityInstallation]: ...
