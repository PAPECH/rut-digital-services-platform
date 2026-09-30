from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.entities import NewsItem
from .models import NewsItemRecord


def _entity(record: NewsItemRecord) -> NewsItem:
    return NewsItem(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        title=record.title,
        title_en=record.title_en,
        body_blocks=record.body_blocks,
        category=record.category,
        cover_attachment_id=record.cover_attachment_id,
        is_active=record.is_active,
        published_at=record.published_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyNewsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: NewsItem) -> NewsItem:
        record = NewsItemRecord(
            bot_instance_id=item.bot_instance_id,
            title=item.title,
            title_en=item.title_en,
            body_blocks=item.body_blocks,
            category=item.category,
            cover_attachment_id=item.cover_attachment_id,
            is_active=item.is_active,
            published_at=item.published_at,
        )
        self._session.add(record)
        self._session.flush()
        return _entity(record)

    def get(self, bot_instance_id: int, item_id: int) -> NewsItem | None:
        record = self._session.execute(
            select(NewsItemRecord).where(
                NewsItemRecord.id == item_id,
                NewsItemRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        return _entity(record) if record else None

    def list_for_bot(self, bot_instance_id: int, *, include_inactive: bool) -> list[NewsItem]:
        query = select(NewsItemRecord).where(NewsItemRecord.bot_instance_id == bot_instance_id)
        if not include_inactive:
            query = query.where(NewsItemRecord.is_active.is_(True))
        query = query.order_by(NewsItemRecord.published_at.desc(), NewsItemRecord.id.desc())
        return [_entity(record) for record in self._session.execute(query).scalars()]

    def patch(self, bot_instance_id: int, item_id: int, merged: NewsItem) -> NewsItem | None:
        record = self._session.execute(
            select(NewsItemRecord).where(
                NewsItemRecord.id == item_id,
                NewsItemRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        if record is None:
            return None
        record.title = merged.title
        record.title_en = merged.title_en
        record.body_blocks = merged.body_blocks
        record.category = merged.category
        record.cover_attachment_id = merged.cover_attachment_id
        record.is_active = merged.is_active
        record.published_at = merged.published_at
        self._session.flush()
        return _entity(record)

    def delete(self, bot_instance_id: int, item_id: int) -> bool:
        record = self._session.execute(
            select(NewsItemRecord).where(
                NewsItemRecord.id == item_id,
                NewsItemRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        if record is None:
            return False
        self._session.delete(record)
        self._session.flush()
        return True
