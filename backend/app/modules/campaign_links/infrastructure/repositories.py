from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domain.entities import (
    CampaignLink,
    CampaignLinkTarget,
    CampaignLinkTouch,
    UnmatchedCodeSummary,
    UnmatchedOpenSource,
)
from .models import CampaignLinkOpenRecord, CampaignLinkRecord, CampaignLinkUnmatchedOpenRecord


def _entity(record: CampaignLinkRecord) -> CampaignLink:
    return CampaignLink(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        code=record.code,
        campaign=record.campaign,
        source=record.source,
        placement=record.placement,
        target=CampaignLinkTarget(record.target),
        created_by_admin_id=record.created_by_admin_id,
        created_at=record.created_at,
        open_count=record.open_count,
        repeat_open_count=record.repeat_open_count,
        last_opened_at=record.last_opened_at,
        deleted_at=record.deleted_at,
    )


class SqlAlchemyCampaignLinkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, link: CampaignLink) -> CampaignLink:
        record = CampaignLinkRecord(
            bot_instance_id=link.bot_instance_id,
            code=link.code,
            campaign=link.campaign,
            source=link.source,
            placement=link.placement,
            target=link.target.value,
            created_by_admin_id=link.created_by_admin_id,
        )
        self._session.add(record)
        self._session.flush()
        return _entity(record)

    def get(self, bot_instance_id: int, link_id: int) -> CampaignLink | None:
        record = self._session.execute(
            select(CampaignLinkRecord).where(
                CampaignLinkRecord.id == link_id,
                CampaignLinkRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        return _entity(record) if record else None

    def get_by_code(self, bot_instance_id: int, code: str) -> CampaignLink | None:
        record = self._session.execute(
            select(CampaignLinkRecord).where(
                CampaignLinkRecord.bot_instance_id == bot_instance_id,
                CampaignLinkRecord.code == code,
                CampaignLinkRecord.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        return _entity(record) if record else None

    def code_exists(self, bot_instance_id: int, code: str) -> bool:
        return self.get_by_code(bot_instance_id, code) is not None

    def list_for_bot(self, bot_instance_id: int) -> list[CampaignLink]:
        records = self._session.execute(
            select(CampaignLinkRecord)
            .where(
                CampaignLinkRecord.bot_instance_id == bot_instance_id,
                CampaignLinkRecord.deleted_at.is_(None),
            )
            .order_by(CampaignLinkRecord.created_at.desc())
        ).scalars()
        return [_entity(record) for record in records]

    def soft_delete(self, bot_instance_id: int, link_id: int) -> CampaignLink | None:
        record = self._session.execute(
            select(CampaignLinkRecord).where(
                CampaignLinkRecord.id == link_id,
                CampaignLinkRecord.bot_instance_id == bot_instance_id,
                CampaignLinkRecord.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if record is None:
            return None
        record.deleted_at = datetime.now(UTC)
        self._session.flush()
        return _entity(record)

    def unique_open_counts(self, bot_instance_id: int, link_ids: list[int]) -> dict[int, int]:
        if not link_ids:
            return {}
        rows = self._session.execute(
            select(
                CampaignLinkOpenRecord.campaign_link_id,
                func.count(func.distinct(CampaignLinkOpenRecord.bot_membership_id)),
            )
            .where(
                CampaignLinkOpenRecord.bot_instance_id == bot_instance_id,
                CampaignLinkOpenRecord.campaign_link_id.in_(link_ids),
            )
            .group_by(CampaignLinkOpenRecord.campaign_link_id)
        ).all()
        return {link_id: count for link_id, count in rows}

    def _find_open_record(self, bot_instance_id: int, code: str) -> CampaignLinkRecord | None:
        return self._session.execute(
            select(CampaignLinkRecord).where(
                CampaignLinkRecord.bot_instance_id == bot_instance_id,
                CampaignLinkRecord.code == code,
                CampaignLinkRecord.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def record_open(
        self, bot_instance_id: int, code: str, *, touch: CampaignLinkTouch
    ) -> CampaignLink | None:
        normalized = code.strip()
        record = self._find_open_record(bot_instance_id, normalized)
        if record is None:
            return None
        now = datetime.now(UTC)
        if touch == CampaignLinkTouch.REPEAT:
            record.repeat_open_count += 1
        else:
            record.open_count += 1
        record.last_opened_at = now
        self._session.flush()
        return _entity(record)

    def record_identified_open(
        self,
        bot_instance_id: int,
        code: str,
        bot_membership_id: int,
    ) -> CampaignLink | None:
        normalized = code.strip()
        record = self._find_open_record(bot_instance_id, normalized)
        if record is None:
            return None
        now = datetime.now(UTC)
        record.open_count += 1
        record.last_opened_at = now
        self._session.add(
            CampaignLinkOpenRecord(
                bot_instance_id=bot_instance_id,
                campaign_link_id=record.id,
                bot_membership_id=bot_membership_id,
                occurred_at=now,
            )
        )
        self._session.flush()
        return _entity(record)

    # --- Unmatched-code capture (Task 074) --------------------------------------------------

    def record_unmatched(
        self, bot_instance_id: int, code: str, *, event_source: UnmatchedOpenSource
    ) -> None:
        self._session.add(
            CampaignLinkUnmatchedOpenRecord(
                bot_instance_id=bot_instance_id,
                code=code,
                event_source=event_source.value,
                occurred_at=datetime.now(UTC),
            )
        )
        self._session.flush()

    def list_unmatched(self, bot_instance_id: int) -> list[UnmatchedCodeSummary]:
        rows = self._session.execute(
            select(
                CampaignLinkUnmatchedOpenRecord.code,
                CampaignLinkUnmatchedOpenRecord.event_source,
                func.count(CampaignLinkUnmatchedOpenRecord.id),
                func.max(CampaignLinkUnmatchedOpenRecord.occurred_at),
            )
            .where(CampaignLinkUnmatchedOpenRecord.bot_instance_id == bot_instance_id)
            .group_by(
                CampaignLinkUnmatchedOpenRecord.code, CampaignLinkUnmatchedOpenRecord.event_source
            )
            .order_by(func.max(CampaignLinkUnmatchedOpenRecord.occurred_at).desc())
        ).all()
        return [
            UnmatchedCodeSummary(
                code=code,
                event_source=UnmatchedOpenSource(event_source),
                hit_count=int(hit_count),
                last_seen_at=last_seen_at,
            )
            for code, event_source, hit_count, last_seen_at in rows
        ]
