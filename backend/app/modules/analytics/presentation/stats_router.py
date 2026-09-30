from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_staff
from ....db.session import get_db
from ....models.enums import (
    MessageDirectionEnum,
    SubmissionStatusEnum,
)
from ....models.form import FormTemplate
from ....models.logger import UserAction
from ...bot_instances.domain.entities import BotInstance
from ...forms.infrastructure.models import FormSubmission, SubmissionStatusHistory
from ...profiles.infrastructure.models import BotMembershipRecord
from ...support_chat.infrastructure.models import Message
from ...tenancy.presentation.dependencies import require_tenant_access
from .stats_schemas import (
    StatsActionItem,
    StatsActions,
    StatsActionTimeseriesItem,
    StatsFormItem,
    StatsForms,
    StatsKpi,
    StatsOverview,
    StatsPeriod,
    StatsTicket,
    StatsTicketTimeseriesItem,
    StatsTimeseriesItem,
)

router = APIRouter()


def get_avg_response_seconds(
    db: Session,
    bot_instance_id: int,
    start: datetime,
    end: datetime,
) -> int:
    next_created_at = (
        func.lead(Message.created_at)
        .over(
            partition_by=Message.user_id,
            order_by=Message.created_at,
        )
        .label("next_created_at")
    )

    next_direction = (
        func.lead(Message.direction)
        .over(
            partition_by=Message.user_id,
            order_by=Message.created_at,
        )
        .label("next_direction")
    )

    next_admin_id = (
        func.lead(Message.replied_by_admin_id)
        .over(
            partition_by=Message.user_id,
            order_by=Message.created_at,
        )
        .label("next_admin_id")
    )

    subquery = (
        select(
            Message.created_at.label("in_created_at"),
            Message.direction.label("current_direction"),
            next_created_at,
            next_direction,
            next_admin_id,
        )
        .where(
            Message.bot_instance_id == bot_instance_id,
            Message.created_at >= start,
            Message.created_at <= end,
        )
        .subquery()
    )

    avg_seconds = db.execute(
        select(func.avg(func.extract("epoch", subquery.c.next_created_at - subquery.c.in_created_at))).where(
            subquery.c.current_direction == MessageDirectionEnum.in_,
            subquery.c.next_direction == MessageDirectionEnum.out,
            subquery.c.next_admin_id.isnot(None),
        )
    ).scalar()

    return int(avg_seconds or 0)


def get_avg_new_to_work_seconds(
    db: Session,
    bot_instance_id: int,
    start: datetime,
    end: datetime,
) -> int:
    first_in_work = (
        select(
            SubmissionStatusHistory.submission_id,
            func.min(SubmissionStatusHistory.changed_at).label("in_work_at"),
        )
        .where(SubmissionStatusHistory.to_status == SubmissionStatusEnum.in_work)
        .group_by(SubmissionStatusHistory.submission_id)
        .subquery()
    )

    avg_time = db.execute(
        select(func.avg(func.extract("epoch", first_in_work.c.in_work_at - FormSubmission.created_at)))
        .join(first_in_work, first_in_work.c.submission_id == FormSubmission.id)
        .where(
            FormSubmission.bot_instance_id == bot_instance_id,
            FormSubmission.created_at >= start,
            FormSubmission.created_at <= end,
        )
    ).scalar()

    return int(avg_time or 0)


def resolve_period(
    days: int,
    date_from: date | None,
    date_to: date | None,
):
    if date_from and date_to:
        start = datetime.combine(
            date_from,
            time.min,
            tzinfo=UTC,
        )
        end = datetime.combine(
            date_to,
            time.max,
            tzinfo=UTC,
        )

        return (
            start,
            end,
            date_from,
            date_to,
        )

    end = datetime.now(UTC)
    start = end - timedelta(days=days)

    return (
        start,
        end,
        start.date(),
        end.date(),
    )


def get_forms(
    db: Session,
    bot_instance_id: int,
    start: datetime,
    end: datetime,
):
    def query(extra=None):
        q = (
            select(
                FormTemplate.id,
                FormTemplate.name,
                func.count(FormSubmission.id),
            )
            .join(
                FormSubmission,
                and_(
                    FormSubmission.form_template_id == FormTemplate.id,
                    FormSubmission.bot_instance_id == bot_instance_id,
                ),
                isouter=True,
            )
            .where(
                FormTemplate.bot_instance_id == bot_instance_id,
                FormSubmission.created_at >= start,
                FormSubmission.created_at <= end,
            )
        )

        if extra is not None:
            q = q.where(extra)

        q = q.group_by(
            FormTemplate.id,
            FormTemplate.name,
        ).order_by(FormTemplate.order)

        return q

    all_rows = db.execute(query()).all()

    new_users_subquery = (
        select(BotMembershipRecord.user_id)
        .where(
            BotMembershipRecord.bot_instance_id == bot_instance_id,
            BotMembershipRecord.created_at >= start,
            BotMembershipRecord.created_at <= end,
        )
        .subquery()
    )

    new_rows = db.execute(
        query(FormSubmission.user_id.in_(select(new_users_subquery.c.user_id)))
    ).all()

    def convert(rows):
        return [
            StatsFormItem(
                form_id=row[0],
                name=row[1],
                count=int(row[2]),
            )
            for row in rows
        ]

    return StatsForms(
        all=convert(all_rows),
        new_users=convert(new_rows),
    )


def get_actions(
    db: Session,
    bot_instance_id: int,
    start: datetime,
    end: datetime,
    mode: str,
):
    if mode == "unique":
        count = func.count(func.distinct(UserAction.user_id))
    else:
        count = func.count(UserAction.id)

    rows = db.execute(
        select(
            UserAction.action_type,
            count,
        )
        .where(
            UserAction.bot_instance_id == bot_instance_id,
            UserAction.created_at >= start,
            UserAction.created_at <= end,
        )
        .group_by(UserAction.action_type)
    ).all()

    return StatsActions(
        mode=mode,
        items=[
            StatsActionItem(
                action_type=row[0].value if hasattr(row[0], "value") else str(row[0]),
                count=int(row[1]),
            )
            for row in rows
        ],
    )


def get_timeseries(
    db: Session,
    bot_instance_id: int,
    start: datetime,
    end: datetime,
):
    day_col = func.date_trunc(
        "day",
        FormSubmission.created_at,
    ).label("day")

    rows = db.execute(
        select(
            day_col,
            func.count(FormSubmission.id),
        )
        .where(
            FormSubmission.bot_instance_id == bot_instance_id,
            FormSubmission.created_at >= start,
            FormSubmission.created_at <= end,
        )
        .group_by(day_col)
        .order_by(day_col)
    ).all()

    return [
        StatsTimeseriesItem(
            day=row[0].date() if row[0] else None,
            count=int(row[1]),
        )
        for row in rows
    ]


def get_kpi(
    db: Session,
    bot_instance_id: int,
    start: datetime,
    end: datetime,
):
    by_status = dict(
        db.execute(
            select(
                FormSubmission.status,
                func.count(FormSubmission.id),
            )
            .where(
                FormSubmission.bot_instance_id == bot_instance_id,
                FormSubmission.created_at >= start,
                FormSubmission.created_at <= end,
            )
            .group_by(FormSubmission.status)
        ).all()
    )

    total = sum(int(v) for v in by_status.values())

    rejected = by_status.get(
        SubmissionStatusEnum.rejected,
        0,
    )

    users_total = (
        db.execute(
            select(func.count(BotMembershipRecord.id)).where(
                BotMembershipRecord.bot_instance_id == bot_instance_id,
                BotMembershipRecord.created_at >= start,
                BotMembershipRecord.created_at <= end,
            )
        ).scalar()
        or 0
    )

    users_with_submission = (
        db.execute(
            select(func.count(func.distinct(FormSubmission.user_id))).where(
                FormSubmission.bot_instance_id == bot_instance_id,
                FormSubmission.created_at >= start,
                FormSubmission.created_at <= end,
            )
        ).scalar()
        or 0
    )

    return StatsKpi(
        total_submissions=total,
        avg_new_to_work_seconds=get_avg_new_to_work_seconds(
            db, bot_instance_id, start, end
        ),
        avg_work_to_done_seconds=0,
        rejected_share=(rejected / total if total else 0),
        users_total=int(users_total),
        users_with_submission=int(users_with_submission),
        conversion_rate=(users_with_submission / users_total if users_total else 0),
    )


def get_tickets(
    db: Session,
    bot_instance_id: int,
    start: datetime,
    end: datetime,
):
    ai_answers = (
        db.execute(
            select(func.count(Message.id)).where(
                Message.bot_instance_id == bot_instance_id,
                Message.is_ai_answered.is_(True),
                Message.created_at >= start,
                Message.created_at <= end,
            )
        ).scalar()
        or 0
    )

    new = (
        db.execute(
            select(func.count(func.distinct(Message.user_id))).where(
                Message.bot_instance_id == bot_instance_id,
                Message.direction == MessageDirectionEnum.in_,
                Message.created_at >= start,
                Message.created_at <= end,
            )
        ).scalar()
        or 0
    )

    # текущая логика открытых тикетов
    last_in = (
        select(
            Message.user_id,
            func.max(Message.created_at).label("last_in"),
        )
        .where(
            Message.bot_instance_id == bot_instance_id,
            Message.direction == MessageDirectionEnum.in_,
        )
        .group_by(Message.user_id)
        .subquery()
    )

    last_out = (
        select(
            Message.user_id,
            func.max(Message.created_at).label("last_out"),
        )
        .where(
            Message.bot_instance_id == bot_instance_id,
            Message.direction == MessageDirectionEnum.out,
            Message.replied_by_admin_id.isnot(None),
        )
        .group_by(Message.user_id)
        .subquery()
    )

    open_count = (
        db.execute(
            select(func.count())
            .select_from(last_in)
            .outerjoin(
                last_out,
                last_in.c.user_id == last_out.c.user_id,
            )
            .where((last_out.c.last_out.is_(None)) | (last_out.c.last_out < last_in.c.last_in))
        ).scalar()
        or 0
    )

    return StatsTicket(
        open=int(open_count),
        new=int(new),
        closed=max(
            int(new) - int(open_count),
            0,
        ),
        avg_response_seconds=get_avg_response_seconds(
            db,
            bot_instance_id,
            start,
            end,
        ),
        ai_answers=int(ai_answers),
    )


def get_tickets_timeseries(
    db: Session,
    bot_instance_id: int,
    start: datetime,
    end: datetime,
):
    """
    Статистика обращений по дням.
    new:
        первый входящий пользовательский месседж за день

    closed:
        первый ответ сотрудника после входящего за день
    """

    # новые обращения
    day_col = func.date_trunc(
        "day",
        Message.created_at,
    ).label("day")

    new_rows = db.execute(
        select(
            day_col,
            func.count(func.distinct(Message.user_id)),
        )
        .where(
            Message.bot_instance_id == bot_instance_id,
            Message.direction == MessageDirectionEnum.in_,
            Message.created_at >= start,
            Message.created_at <= end,
        )
        .group_by(day_col)
        .order_by(day_col)
    ).all()

    new_map = {row[0].date(): int(row[1]) for row in new_rows}

    # закрытые обращения
    #
    # ищем пользователей,
    # у которых был ответ сотрудника
    #

    day_col = func.date_trunc(
        "day",
        Message.created_at,
    ).label("day")
    closed_rows = db.execute(
        select(
            day_col,
            func.count(func.distinct(Message.user_id)),
        )
        .where(
            Message.bot_instance_id == bot_instance_id,
            Message.direction == MessageDirectionEnum.out,
            Message.replied_by_admin_id.isnot(None),
            Message.is_ai_answered.is_(False),
            Message.created_at >= start,
            Message.created_at <= end,
        )
        .group_by(day_col)
        .order_by(day_col)
    ).all()

    closed_map = {row[0].date(): int(row[1]) for row in closed_rows}

    days = set(new_map.keys()) | set(closed_map.keys())

    return [
        StatsTicketTimeseriesItem(
            day=day,
            new=new_map.get(day, 0),
            closed=closed_map.get(day, 0),
        )
        for day in sorted(days)
    ]


def get_actions_timeseries(
    db: Session,
    bot_instance_id: int,
    start: datetime,
    end: datetime,
    mode: str,
):
    if mode == "unique":
        count_expr = func.count(func.distinct(UserAction.user_id))
    else:
        count_expr = func.count(UserAction.id)

    day_col = func.date_trunc(
        "day",
        UserAction.created_at,
    ).label("day")

    stmt = (
        select(
            day_col,
            UserAction.action_type,
            count_expr.label("count"),
        )
        .where(
            UserAction.bot_instance_id == bot_instance_id,
            UserAction.created_at >= start,
            UserAction.created_at <= end,
        )
        .group_by(
            day_col,
            UserAction.action_type,
        )
        .order_by(
            day_col,
        )
    )

    rows = db.execute(stmt).all()

    return [
        StatsActionTimeseriesItem(
            day=row[0].date(),
            action_type=(row[1].value if hasattr(row[1], "value") else str(row[1])),
            count=int(row[2]),
        )
        for row in rows
    ]


@router.get(
    "/overview",
    response_model=StatsOverview,
)
def overview(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
    ),
    date_from: date | None = None,
    date_to: date | None = None,
    action_mode: str = Query(
        default="all",
        pattern="^(all|unique)$",
    ),
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
):
    start, end, start_date, end_date = resolve_period(
        days,
        date_from,
        date_to,
    )

    return StatsOverview(
        period=StatsPeriod(
            date_from=start_date,
            date_to=end_date,
        ),
        kpi=get_kpi(
            db,
            bot.id,
            start,
            end,
        ),
        forms=get_forms(
            db,
            bot.id,
            start,
            end,
        ),
        actions=get_actions(
            db,
            bot.id,
            start,
            end,
            action_mode,
        ),
        tickets=get_tickets(
            db,
            bot.id,
            start,
            end,
        ),
        timeseries=get_timeseries(
            db,
            bot.id,
            start,
            end,
        ),
        tickets_timeseries=get_tickets_timeseries(
            db,
            bot.id,
            start,
            end,
        ),
        actions_timeseries=get_actions_timeseries(
            db,
            bot.id,
            start,
            end,
            action_mode,
        ),
    )
