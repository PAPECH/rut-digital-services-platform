from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.settings import Setting
from .models import AppSetting


def _to_domain(record: AppSetting) -> Setting:
    return Setting(bot_instance_id=record.bot_instance_id, key=record.key, value=record.value)


class SqlAlchemySettingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, bot_instance_id: int, key: str) -> Setting | None:
        record = self._db.get(AppSetting, (bot_instance_id, key))
        return _to_domain(record) if record else None

    def list_for_bot(self, bot_instance_id: int) -> list[Setting]:
        records = self._db.execute(
            select(AppSetting)
            .where(AppSetting.bot_instance_id == bot_instance_id)
            .order_by(AppSetting.key)
        ).scalars()
        return [_to_domain(record) for record in records]

    def upsert(self, bot_instance_id: int, key: str, value: str | None) -> Setting:
        record = self._db.get(AppSetting, (bot_instance_id, key))
        if record is None:
            record = AppSetting(bot_instance_id=bot_instance_id, key=key, value=value)
            self._db.add(record)
        else:
            record.value = value
        self._db.commit()
        self._db.refresh(record)
        return _to_domain(record)

    def delete(self, bot_instance_id: int, key: str) -> bool:
        record = self._db.get(AppSetting, (bot_instance_id, key))
        if record is None:
            return False
        self._db.delete(record)
        self._db.commit()
        return True
