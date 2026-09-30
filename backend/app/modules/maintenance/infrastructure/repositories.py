from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.policies import MaintenanceMode, MaintenancePolicy
from .models import MaintenancePolicyRecord


def _to_domain(record: MaintenancePolicyRecord) -> MaintenancePolicy:
    return MaintenancePolicy(
        scope_key=record.scope_key,
        bot_instance_id=record.bot_instance_id,
        mode=MaintenanceMode(record.mode),
        title=record.title,
        message=record.message,
        starts_at=record.starts_at,
        ends_at=record.ends_at,
        retry_after_seconds=record.retry_after_seconds,
        allow_admin=record.allow_admin,
    )


class SqlAlchemyMaintenanceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, scope_key: str) -> MaintenancePolicy | None:
        record = self._session.execute(
            select(MaintenancePolicyRecord).where(MaintenancePolicyRecord.scope_key == scope_key)
        ).scalar_one_or_none()
        return _to_domain(record) if record else None

    def save(self, policy: MaintenancePolicy, *, updated_by: int | None) -> MaintenancePolicy:
        record = self._session.execute(
            select(MaintenancePolicyRecord).where(MaintenancePolicyRecord.scope_key == policy.scope_key)
        ).scalar_one_or_none()
        if record is None:
            record = MaintenancePolicyRecord(scope_key=policy.scope_key)
            self._session.add(record)
        record.bot_instance_id = policy.bot_instance_id
        record.mode = policy.mode.value
        record.title = policy.title
        record.message = policy.message
        record.starts_at = policy.starts_at
        record.ends_at = policy.ends_at
        record.retry_after_seconds = policy.retry_after_seconds
        record.allow_admin = policy.allow_admin
        record.updated_by = updated_by
        self._session.flush()
        return _to_domain(record)
