from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..application.use_cases import CapabilityConfigRevisionConflict
from ..domain.entities import CapabilityInstallation
from .models import CapabilityInstallationRecord


def _installation(record: CapabilityInstallationRecord) -> CapabilityInstallation:
    return CapabilityInstallation(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        capability_key=record.capability_key,
        is_enabled=record.is_enabled,
        order=record.order,
        config=dict(record.config or {}),
        config_revision=record.config_revision,
        configured_by=record.configured_by,
        enabled_by=record.enabled_by,
        last_health_status=record.last_health_status,
        last_health_at=record.last_health_at,
        last_health_error_code=record.last_health_error_code,
    )


class SqlAlchemyCapabilityInstallationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_bot(self, bot_instance_id: int) -> list[CapabilityInstallation]:
        records = self._session.execute(
            select(CapabilityInstallationRecord)
            .where(CapabilityInstallationRecord.bot_instance_id == bot_instance_id)
            .order_by(CapabilityInstallationRecord.order, CapabilityInstallationRecord.id)
        ).scalars()
        return [_installation(record) for record in records]

    def get(self, bot_instance_id: int, capability_key: str) -> CapabilityInstallation | None:
        record = self._session.execute(
            select(CapabilityInstallationRecord).where(
                CapabilityInstallationRecord.bot_instance_id == bot_instance_id,
                CapabilityInstallationRecord.capability_key == capability_key,
            )
        ).scalar_one_or_none()
        return _installation(record) if record else None

    def create(self, installation: CapabilityInstallation) -> CapabilityInstallation:
        record = CapabilityInstallationRecord(
            bot_instance_id=installation.bot_instance_id,
            capability_key=installation.capability_key,
            is_enabled=installation.is_enabled,
            order=installation.order,
            config=installation.config,
            config_revision=installation.config_revision,
            configured_by=installation.configured_by,
            enabled_by=installation.enabled_by,
            last_health_status=installation.last_health_status,
            last_health_at=installation.last_health_at,
            last_health_error_code=installation.last_health_error_code,
        )
        self._session.add(record)
        self._session.flush()
        return _installation(record)

    def save(
        self,
        installation: CapabilityInstallation,
        *,
        expected_revision: int | None = None,
    ) -> CapabilityInstallation:
        assert installation.id is not None
        conditions = [
            CapabilityInstallationRecord.id == installation.id,
            CapabilityInstallationRecord.bot_instance_id == installation.bot_instance_id,
        ]
        if expected_revision is not None:
            conditions.append(CapabilityInstallationRecord.config_revision == expected_revision)
        result = self._session.execute(
            update(CapabilityInstallationRecord)
            .where(*conditions)
            .values(
                is_enabled=installation.is_enabled,
                order=installation.order,
                config=installation.config,
                config_revision=installation.config_revision,
                configured_by=installation.configured_by,
                enabled_by=installation.enabled_by,
                last_health_status=installation.last_health_status,
                last_health_at=installation.last_health_at,
                last_health_error_code=installation.last_health_error_code,
            )
            .returning(CapabilityInstallationRecord)
        ).scalar_one_or_none()
        if result is None:
            raise CapabilityConfigRevisionConflict(installation.capability_key)
        self._session.flush()
        return _installation(result)

    def reorder(
        self,
        bot_instance_id: int,
        capability_keys: list[str],
    ) -> list[CapabilityInstallation]:
        records = list(
            self._session.execute(
                select(CapabilityInstallationRecord)
                .where(CapabilityInstallationRecord.bot_instance_id == bot_instance_id)
                .with_for_update()
            ).scalars()
        )
        if {record.capability_key for record in records} != set(capability_keys):
            raise ValueError("Capability order must include every installation in the current bot")
        by_key = {record.capability_key: record for record in records}
        for order, capability_key in enumerate(capability_keys):
            by_key[capability_key].order = order
        self._session.flush()
        return [_installation(by_key[key]) for key in capability_keys]
