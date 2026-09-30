from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.entities import BotMembership, SharedProfile
from .models import BotMembershipRecord, User


def _profile(record: User) -> SharedProfile:
    return SharedProfile(
        user_id=record.id,
        external_user_id=record.user_id,
        provider=record.system.value,
        first_name=record.first_name,
        last_name=record.last_name,
        patronymic=record.patronymic,
        phone=record.phone,
        phone_verified=record.phone_verified,
        email=record.email,
        birth_date=record.birth_date,
        job_title=record.job_title,
        structural_unit=record.structural_unit,
        shared_data=dict(record.shared_data or {}),
    )


def _membership(record: BotMembershipRecord) -> BotMembership:
    return BotMembership(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        user_id=record.user_id,
        is_active=record.is_active,
        local_data=dict(record.local_data or {}),
        ban_chat=record.ban_chat,
        ban_chat_reason=record.ban_chat_reason,
        ban_forms=record.ban_forms,
        ban_forms_reason=record.ban_forms_reason,
        ban_app=record.ban_app,
        ban_app_reason=record.ban_app_reason,
        source_campaign_link_id=record.source_campaign_link_id,
    )


class SqlAlchemyProfileGateway:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_shared_profile(self, user_id: int) -> SharedProfile | None:
        record = self._session.get(User, user_id)
        return _profile(record) if record else None

    def update_shared_profile(self, user_id: int, values: dict[str, Any]) -> SharedProfile:
        record = self._session.get(User, user_id)
        if record is None:
            raise LookupError(user_id)
        allowed = {
            "first_name",
            "last_name",
            "patronymic",
            "email",
            "birth_date",
            "study_group",
            "job_title",
            "structural_unit",
            "shared_data",
        }
        for key, value in values.items():
            if key in allowed:
                setattr(record, key, value)
        self._session.flush()
        return _profile(record)

    def get_membership(self, bot_instance_id: int, user_id: int) -> BotMembership | None:
        record = self._session.execute(
            select(BotMembershipRecord).where(
                BotMembershipRecord.bot_instance_id == bot_instance_id,
                BotMembershipRecord.user_id == user_id,
            )
        ).scalar_one_or_none()
        return _membership(record) if record else None

    def create_membership(self, membership: BotMembership) -> BotMembership:
        record = BotMembershipRecord(
            bot_instance_id=membership.bot_instance_id,
            user_id=membership.user_id,
            is_active=membership.is_active,
            local_data=membership.local_data,
            ban_chat=membership.ban_chat,
            ban_chat_reason=membership.ban_chat_reason,
            ban_forms=membership.ban_forms,
            ban_forms_reason=membership.ban_forms_reason,
            ban_app=membership.ban_app,
            ban_app_reason=membership.ban_app_reason,
        )
        self._session.add(record)
        self._session.flush()
        return _membership(record)

    def update_membership_data(
        self,
        bot_instance_id: int,
        user_id: int,
        values: dict[str, Any],
    ) -> BotMembership:
        record = self._session.execute(
            select(BotMembershipRecord).where(
                BotMembershipRecord.bot_instance_id == bot_instance_id,
                BotMembershipRecord.user_id == user_id,
            )
        ).scalar_one_or_none()
        if record is None:
            raise LookupError((bot_instance_id, user_id))
        record.local_data = {**dict(record.local_data or {}), **values}
        self._session.flush()
        return _membership(record)

    def set_membership_campaign_source(
        self,
        bot_instance_id: int,
        user_id: int,
        campaign_link_id: int,
    ) -> None:
        record = self._session.execute(
            select(BotMembershipRecord).where(
                BotMembershipRecord.bot_instance_id == bot_instance_id,
                BotMembershipRecord.user_id == user_id,
            )
        ).scalar_one_or_none()
        if record is None or record.source_campaign_link_id is not None:
            return
        record.source_campaign_link_id = campaign_link_id
        self._session.flush()
