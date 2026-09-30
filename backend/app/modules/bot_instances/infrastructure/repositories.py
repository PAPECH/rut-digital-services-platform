from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.entities import BotInstance
from .models import BotInstanceRecord


def _to_domain(record: BotInstanceRecord) -> BotInstance:
    deleted_at = record.deleted_at
    if deleted_at is not None and deleted_at.tzinfo is None:
        deleted_at = deleted_at.replace(tzinfo=timezone.utc)
    return BotInstance(
        id=record.id,
        slug=record.slug,
        name=record.name,
        description=record.description,
        is_active=record.is_active,
        order=record.order,
        branding=dict(record.branding or {}),
        settings=dict(record.settings or {}),
        profile_schema=list(record.profile_schema or []),
        deleted_at=deleted_at,
    )


class SqlAlchemyBotInstanceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, bot: BotInstance) -> BotInstance:
        record = BotInstanceRecord(
            slug=bot.slug,
            name=bot.name,
            description=bot.description,
            is_active=bot.is_active,
            order=bot.order,
            branding=bot.branding,
            settings=bot.settings,
            profile_schema=bot.profile_schema,
        )
        self._session.add(record)
        self._session.flush()
        return _to_domain(record)

    def get(self, bot_id: int) -> BotInstance | None:
        record = self._session.get(BotInstanceRecord, bot_id)
        return _to_domain(record) if record else None

    def get_by_slug(self, slug: str) -> BotInstance | None:
        # Only a live bot claims its slug -- a soft-deleted bot's slug is free to reuse.
        record = self._session.execute(
            select(BotInstanceRecord).where(
                BotInstanceRecord.slug == slug.strip().lower(),
                BotInstanceRecord.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        return _to_domain(record) if record else None

    def list_all(self, *, include_deleted: bool = False) -> list[BotInstance]:
        query = select(BotInstanceRecord).order_by(BotInstanceRecord.order, BotInstanceRecord.id)
        if not include_deleted:
            query = query.where(BotInstanceRecord.deleted_at.is_(None))
        records = self._session.execute(query).scalars()
        return [_to_domain(record) for record in records]

    def update(self, bot: BotInstance) -> BotInstance:
        if bot.id is None:
            raise ValueError("Cannot update a bot without an ID")
        record = self._session.get(BotInstanceRecord, bot.id)
        if record is None:
            raise LookupError(bot.id)
        record.name = bot.name
        record.description = bot.description
        record.is_active = bot.is_active
        record.order = bot.order
        record.branding = bot.branding
        record.settings = bot.settings
        record.profile_schema = bot.profile_schema
        self._session.flush()
        return _to_domain(record)

    def soft_delete(self, bot_id: int) -> BotInstance:
        record = self._session.get(BotInstanceRecord, bot_id)
        if record is None:
            raise LookupError(bot_id)
        record.deleted_at = datetime.now(tz=timezone.utc)
        record.is_active = False
        self._session.flush()
        return _to_domain(record)

    def restore(self, bot_id: int) -> BotInstance:
        record = self._session.get(BotInstanceRecord, bot_id)
        if record is None:
            raise LookupError(bot_id)
        record.deleted_at = None
        self._session.flush()
        return _to_domain(record)
