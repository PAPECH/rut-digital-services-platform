from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..domain.entities import RequestStatusState, RequestStatusSubscription
from .models import RequestStatusStateRecord, RequestStatusSubscriptionRecord


def _state(record: RequestStatusStateRecord) -> RequestStatusState:
    return RequestStatusState(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        installation_id=record.installation_id,
        request_number=record.request_number,
        request_number_hash=record.request_number_hash,
        last_status=record.last_status,
        checked_at=record.checked_at,
        source_revision=record.source_revision,
    )


def _subscription(record: RequestStatusSubscriptionRecord) -> RequestStatusSubscription:
    return RequestStatusSubscription(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        installation_id=record.installation_id,
        user_id=record.user_id,
        request_number=record.request_number,
        request_number_hash=record.request_number_hash,
        is_active=record.is_active,
    )


class SqlAlchemyRequestStatusRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_state(self, bot_instance_id: int, number_hash: str) -> RequestStatusState | None:
        record = self._session.execute(
            select(RequestStatusStateRecord).where(
                RequestStatusStateRecord.bot_instance_id == bot_instance_id,
                RequestStatusStateRecord.request_number_hash == number_hash,
            )
        ).scalar_one_or_none()
        return _state(record) if record else None

    def upsert_states(self, states: list[RequestStatusState]) -> None:
        for state in states:
            statement = insert(RequestStatusStateRecord).values(
                bot_instance_id=state.bot_instance_id,
                installation_id=state.installation_id,
                request_number=state.request_number,
                request_number_hash=state.request_number_hash,
                last_status=state.last_status,
                checked_at=state.checked_at,
                source_revision=state.source_revision,
            )
            self._session.execute(
                statement.on_conflict_do_update(
                    constraint="uq_request_status_state_bot_hash",
                    set_={
                        "installation_id": statement.excluded.installation_id,
                        "request_number": statement.excluded.request_number,
                        "last_status": statement.excluded.last_status,
                        "checked_at": statement.excluded.checked_at,
                        "source_revision": RequestStatusStateRecord.source_revision + 1,
                    },
                )
            )
        self._session.flush()

    def get_subscription(
        self,
        bot_instance_id: int,
        user_id: int,
        number_hash: str | None = None,
    ) -> RequestStatusSubscription | None:
        query = select(RequestStatusSubscriptionRecord).where(
            RequestStatusSubscriptionRecord.bot_instance_id == bot_instance_id,
            RequestStatusSubscriptionRecord.user_id == user_id,
        )
        if number_hash is not None:
            query = query.where(RequestStatusSubscriptionRecord.request_number_hash == number_hash)
        else:
            query = query.order_by(RequestStatusSubscriptionRecord.updated_at.desc()).limit(1)
        record = self._session.execute(query).scalar_one_or_none()
        return _subscription(record) if record else None

    def save_subscription(
        self,
        subscription: RequestStatusSubscription,
    ) -> RequestStatusSubscription:
        record = self._session.execute(
            select(RequestStatusSubscriptionRecord).where(
                RequestStatusSubscriptionRecord.bot_instance_id == subscription.bot_instance_id,
                RequestStatusSubscriptionRecord.user_id == subscription.user_id,
                RequestStatusSubscriptionRecord.request_number_hash == subscription.request_number_hash,
            )
        ).scalar_one_or_none()
        if record is None:
            record = RequestStatusSubscriptionRecord(
                bot_instance_id=subscription.bot_instance_id,
                installation_id=subscription.installation_id,
                user_id=subscription.user_id,
                request_number=subscription.request_number,
                request_number_hash=subscription.request_number_hash,
                is_active=subscription.is_active,
            )
            self._session.add(record)
        else:
            record.is_active = subscription.is_active
            record.installation_id = subscription.installation_id
        self._session.flush()
        return _subscription(record)
