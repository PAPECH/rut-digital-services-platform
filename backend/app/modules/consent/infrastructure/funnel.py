from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .models import ConsentFunnelCounterRecord


class ConsentFunnelEvent(StrEnum):
    """Fully anonymous -- no user identifier travels with these, by design. See
    docs/tasks/064, 'Metrics for people who haven't consented yet': UserAction and
    AnalyticsEvent both hard-require a real, positive internal user_id, which someone
    ungated by definition doesn't have."""

    gate_shown = "gate_shown"
    gate_accepted = "gate_accepted"


def bump_consent_funnel(db: Session, bot_instance_id: int, event: ConsentFunnelEvent) -> None:
    today = datetime.now(tz=UTC).date()
    stmt = insert(ConsentFunnelCounterRecord).values(
        bot_instance_id=bot_instance_id,
        event_type=event.value,
        day=today,
        count=1,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            ConsentFunnelCounterRecord.bot_instance_id,
            ConsentFunnelCounterRecord.event_type,
            ConsentFunnelCounterRecord.day,
        ],
        set_={"count": ConsentFunnelCounterRecord.count + 1},
    )
    db.execute(stmt)
