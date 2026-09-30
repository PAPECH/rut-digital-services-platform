from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, func, select, union_all
from sqlalchemy.orm import Session

from ....models.enums import MessageDirectionEnum, SubmissionStatusEnum
from ....models.logger import UserAction
from ....modules.support_chat.infrastructure.models import Message
from ...bot_instances.infrastructure.models import BotInstanceRecord
from ...campaign_links.infrastructure.models import (
    CampaignLinkOpenRecord,
    CampaignLinkRecord,
    CampaignLinkUnmatchedOpenRecord,
)
from ...content.infrastructure.models import ContentVersionRecord
from ...forms.infrastructure.models import (
    FormDefinitionRecord,
    FormSubmission,
    SubmissionStatusHistory,
)
from ...profiles.infrastructure.models import BotMembershipRecord
from ..domain.dashboard import (
    BotComparison,
    BotDashboard,
    BotSummary,
    BotTrendPoint,
    CampaignLinkMetric,
    CapabilityMetric,
    ContentMetric,
    DashboardPeriod,
    FormMetric,
    FunnelStep,
    PlatformDashboard,
    PlatformSummary,
    PlatformTrendPoint,
    TicketTrendPoint,
)
from ..domain.events import AnalyticsEventName

CONTENT_ACTIONS = (
    AnalyticsEventName.CONTENT_CATEGORY_OPEN.value,
    AnalyticsEventName.CONTENT_TAB_OPEN.value,
    AnalyticsEventName.CONTENT_BLOCK_INTERACTION.value,
)
CAPABILITY_ACTIONS = (
    AnalyticsEventName.CAPABILITY_VIEW_OPEN.value,
    AnalyticsEventName.CAPABILITY_LOOKUP_COMPLETE.value,
    AnalyticsEventName.CAPABILITY_SUBSCRIPTION_CHANGED.value,
)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _day(column: Any) -> Any:
    return func.date_trunc("day", func.timezone("Europe/Moscow", column))


def _row_day(value: Any) -> date:
    return value.date() if isinstance(value, datetime) else value


def _period_days(period: DashboardPeriod) -> list[date]:
    span = (period.date_to - period.date_from).days
    return [period.date_from + timedelta(days=offset) for offset in range(span + 1)]


def _iter_blocks(blocks: list[dict[str, Any]]):
    for block in blocks:
        yield block
        if block.get("type") == "tabs":
            for tab in block.get("tabs", []):
                yield from _iter_blocks(tab.get("blocks", []))


class SqlAlchemyDashboardRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _ids_filter(column: Any, bot_ids: tuple[int, ...]) -> Any:
        return column == bot_ids[0] if len(bot_ids) == 1 else column.in_(bot_ids)

    def _activity(self, bot_ids: tuple[int, ...], period: DashboardPeriod):
        return union_all(
            select(
                UserAction.bot_instance_id.label("bot_id"),
                UserAction.user_id.label("user_id"),
                UserAction.created_at.label("occurred_at"),
            ).where(
                self._ids_filter(UserAction.bot_instance_id, bot_ids),
                UserAction.created_at >= period.start,
                UserAction.created_at < period.end,
            ),
            select(
                FormSubmission.bot_instance_id.label("bot_id"),
                FormSubmission.user_id.label("user_id"),
                FormSubmission.created_at.label("occurred_at"),
            ).where(
                self._ids_filter(FormSubmission.bot_instance_id, bot_ids),
                FormSubmission.created_at >= period.start,
                FormSubmission.created_at < period.end,
            ),
            select(
                Message.bot_instance_id.label("bot_id"),
                Message.user_id.label("user_id"),
                Message.created_at.label("occurred_at"),
            ).where(
                self._ids_filter(Message.bot_instance_id, bot_ids),
                Message.direction == MessageDirectionEnum.in_,
                Message.created_at >= period.start,
                Message.created_at < period.end,
            ),
        ).subquery()

    def _open_tickets(self, bot_ids: tuple[int, ...], end: datetime) -> int:
        last_in = (
            select(
                Message.bot_instance_id.label("bot_id"),
                Message.user_id.label("user_id"),
                func.max(Message.created_at).label("last_in"),
            )
            .where(
                self._ids_filter(Message.bot_instance_id, bot_ids),
                Message.direction == MessageDirectionEnum.in_,
                Message.created_at < end,
            )
            .group_by(Message.bot_instance_id, Message.user_id)
            .subquery()
        )
        last_out = (
            select(
                Message.bot_instance_id.label("bot_id"),
                Message.user_id.label("user_id"),
                func.max(Message.created_at).label("last_out"),
            )
            .where(
                self._ids_filter(Message.bot_instance_id, bot_ids),
                Message.direction == MessageDirectionEnum.out,
                Message.created_at < end,
            )
            .group_by(Message.bot_instance_id, Message.user_id)
            .subquery()
        )
        value = self._session.execute(
            select(func.count())
            .select_from(last_in)
            .outerjoin(
                last_out,
                and_(
                    last_in.c.bot_id == last_out.c.bot_id,
                    last_in.c.user_id == last_out.c.user_id,
                ),
            )
            .where(
                (last_out.c.last_out.is_(None))
                | (last_out.c.last_out < last_in.c.last_in)
            )
        ).scalar()
        return int(value or 0)

    def _avg_response_seconds(
        self,
        bot_ids: tuple[int, ...],
        period: DashboardPeriod,
    ) -> int:
        # Each outgoing message closes a segment of the conversation. A staff reply is measured
        # from the first incoming message of the segment it closes, so several questions in a
        # row count as one wait that started with the first of them.
        is_out = case((Message.direction == MessageDirectionEnum.out, 1), else_=0)
        segment = func.sum(is_out).over(
            partition_by=(Message.bot_instance_id, Message.user_id),
            order_by=(Message.created_at, Message.id),
        )
        rows = (
            select(
                Message.bot_instance_id.label("bot_id"),
                Message.user_id.label("user_id"),
                Message.direction.label("direction"),
                Message.replied_by_admin_id.label("admin_id"),
                Message.created_at.label("created_at"),
                segment.label("segment"),
            )
            .where(
                self._ids_filter(Message.bot_instance_id, bot_ids),
                Message.created_at < period.end,
            )
            .subquery()
        )
        waits = (
            select(
                rows.c.bot_id,
                rows.c.user_id,
                rows.c.segment,
                func.min(rows.c.created_at).label("first_in"),
            )
            .where(rows.c.direction == MessageDirectionEnum.in_)
            .group_by(rows.c.bot_id, rows.c.user_id, rows.c.segment)
            .subquery()
        )
        value = self._session.execute(
            select(func.avg(func.extract("epoch", rows.c.created_at - waits.c.first_in)))
            .select_from(rows)
            .join(
                waits,
                and_(
                    waits.c.bot_id == rows.c.bot_id,
                    waits.c.user_id == rows.c.user_id,
                    waits.c.segment == rows.c.segment - 1,
                ),
            )
            .where(
                rows.c.direction == MessageDirectionEnum.out,
                rows.c.admin_id.isnot(None),
                rows.c.created_at >= period.start,
            )
        ).scalar()
        return int(value or 0)

    def _workflow_averages(
        self,
        bot_ids: tuple[int, ...],
        period: DashboardPeriod,
    ) -> tuple[int, int, int]:
        first_in_work = (
            select(
                SubmissionStatusHistory.submission_id,
                func.min(SubmissionStatusHistory.changed_at).label("in_work_at"),
            )
            .where(SubmissionStatusHistory.to_status == SubmissionStatusEnum.in_work)
            .group_by(SubmissionStatusHistory.submission_id)
            .subquery()
        )
        first_done = (
            select(
                SubmissionStatusHistory.submission_id,
                func.min(SubmissionStatusHistory.changed_at).label("done_at"),
            )
            .where(SubmissionStatusHistory.to_status == SubmissionStatusEnum.done)
            .group_by(SubmissionStatusHistory.submission_id)
            .subquery()
        )
        base_filters = (
            self._ids_filter(FormSubmission.bot_instance_id, bot_ids),
            FormSubmission.created_at >= period.start,
            FormSubmission.created_at < period.end,
        )
        new_to_work = self._session.execute(
            select(
                func.avg(
                    func.extract("epoch", first_in_work.c.in_work_at - FormSubmission.created_at)
                )
            )
            .select_from(FormSubmission)
            .join(first_in_work, first_in_work.c.submission_id == FormSubmission.id)
            .where(*base_filters)
        ).scalar()
        work_to_done = self._session.execute(
            select(
                func.avg(func.extract("epoch", first_done.c.done_at - first_in_work.c.in_work_at))
            )
            .select_from(FormSubmission)
            .join(first_in_work, first_in_work.c.submission_id == FormSubmission.id)
            .join(first_done, first_done.c.submission_id == FormSubmission.id)
            .where(*base_filters, first_done.c.done_at >= first_in_work.c.in_work_at)
        ).scalar()
        new_to_done = self._session.execute(
            select(func.avg(func.extract("epoch", first_done.c.done_at - FormSubmission.created_at)))
            .select_from(FormSubmission)
            .join(first_done, first_done.c.submission_id == FormSubmission.id)
            .where(*base_filters)
        ).scalar()
        return int(new_to_work or 0), int(work_to_done or 0), int(new_to_done or 0)

    def _bot_summary(self, bot_id: int, period: DashboardPeriod) -> BotSummary:
        bot_ids = (bot_id,)
        activity = self._activity(bot_ids, period)
        active_users = self._session.execute(
            select(func.count(func.distinct(activity.c.user_id)))
        ).scalar()
        new_users = self._session.execute(
            select(func.count(BotMembershipRecord.id)).where(
                BotMembershipRecord.bot_instance_id == bot_id,
                BotMembershipRecord.created_at >= period.start,
                BotMembershipRecord.created_at < period.end,
            )
        ).scalar()
        submissions, submitters = self._session.execute(
            select(
                func.count(FormSubmission.id),
                func.count(func.distinct(FormSubmission.user_id)),
            ).where(
                FormSubmission.bot_instance_id == bot_id,
                FormSubmission.created_at >= period.start,
                FormSubmission.created_at < period.end,
            )
        ).one()
        ai_answers = self._session.execute(
            select(func.count(Message.id)).where(
                Message.bot_instance_id == bot_id,
                Message.direction == MessageDirectionEnum.in_,
                Message.is_ai_answered.is_(True),
                Message.created_at >= period.start,
                Message.created_at < period.end,
            )
        ).scalar()
        content_interactions = self._session.execute(
            select(func.count(UserAction.id)).where(
                UserAction.bot_instance_id == bot_id,
                UserAction.action_type.in_(CONTENT_ACTIONS),
                UserAction.created_at >= period.start,
                UserAction.created_at < period.end,
            )
        ).scalar()
        capability_uses = self._session.execute(
            select(func.count(UserAction.id)).where(
                UserAction.bot_instance_id == bot_id,
                UserAction.action_type.in_(CAPABILITY_ACTIONS),
                UserAction.created_at >= period.start,
                UserAction.created_at < period.end,
            )
        ).scalar()
        avg_new_to_work, avg_work_to_done, avg_new_to_done = self._workflow_averages(
            bot_ids, period
        )
        campaign_opens, campaign_unique_opens = self._campaign_link_totals(bot_ids, period)
        campaign_repeat_opens, campaign_unmatched_opens = self._campaign_link_repeat_and_unmatched(
            bot_ids, period
        )
        return BotSummary(
            active_users=int(active_users or 0),
            new_users=int(new_users or 0),
            submissions=int(submissions or 0),
            submitters=int(submitters or 0),
            conversion_rate=_ratio(int(submitters or 0), int(active_users or 0)),
            open_tickets=self._open_tickets(bot_ids, period.end),
            avg_response_seconds=self._avg_response_seconds(bot_ids, period),
            avg_new_to_work_seconds=avg_new_to_work,
            avg_work_to_done_seconds=avg_work_to_done,
            avg_new_to_done_seconds=avg_new_to_done,
            ai_answers=int(ai_answers or 0),
            content_interactions=int(content_interactions or 0),
            capability_uses=int(capability_uses or 0),
            campaign_link_opens=campaign_opens,
            campaign_link_unique_opens=campaign_unique_opens,
            campaign_link_repeat_opens=campaign_repeat_opens,
            campaign_link_unmatched_opens=campaign_unmatched_opens,
        )

    def _funnel(self, bot_id: int, period: DashboardPeriod) -> tuple[FunnelStep, ...]:
        steps = (
            (AnalyticsEventName.APP_OPEN.value, "Открыли приложение"),
            (AnalyticsEventName.CONTENT_CATEGORY_OPEN.value, "Открыли категорию"),
            (AnalyticsEventName.FORM_OPEN.value, "Открыли форму"),
            (AnalyticsEventName.FORM_START.value, "Начали заполнение"),
            (AnalyticsEventName.SUBMIT_FORM.value, "Отправили форму"),
        )
        rows = self._session.execute(
            select(
                UserAction.action_type,
                func.count(UserAction.id),
                func.count(func.distinct(UserAction.user_id)),
            )
            .where(
                UserAction.bot_instance_id == bot_id,
                UserAction.action_type.in_([item[0] for item in steps]),
                UserAction.created_at >= period.start,
                UserAction.created_at < period.end,
            )
            .group_by(UserAction.action_type)
        ).all()
        counts = {str(row[0]): (int(row[1]), int(row[2])) for row in rows}
        return tuple(
            FunnelStep(key=key, label=label, total=counts.get(key, (0, 0))[0], unique_users=counts.get(key, (0, 0))[1])
            for key, label in steps
        )

    def _bot_trend(self, bot_id: int, period: DashboardPeriod) -> tuple[BotTrendPoint, ...]:
        activity = self._activity((bot_id,), period)
        activity_day = _day(activity.c.occurred_at).label("day")
        activity_rows = self._session.execute(
            select(activity_day, func.count(func.distinct(activity.c.user_id)))
            .group_by(activity_day)
            .order_by(activity_day)
        ).all()
        submission_day = _day(FormSubmission.created_at).label("day")
        submission_rows = self._session.execute(
            select(submission_day, func.count(FormSubmission.id))
            .where(
                FormSubmission.bot_instance_id == bot_id,
                FormSubmission.created_at >= period.start,
                FormSubmission.created_at < period.end,
            )
            .group_by(submission_day)
            .order_by(submission_day)
        ).all()
        active_map = {_row_day(row[0]): int(row[1]) for row in activity_rows}
        submissions_map = {_row_day(row[0]): int(row[1]) for row in submission_rows}
        days = _period_days(period)
        return tuple(
            BotTrendPoint(
                day=item,
                active_users=active_map.get(item, 0),
                submissions=submissions_map.get(item, 0),
            )
            for item in days
        )

    def _forms(self, bot_id: int, period: DashboardPeriod) -> tuple[FormMetric, ...]:
        definitions = self._session.execute(
            select(FormDefinitionRecord.id, FormDefinitionRecord.name).where(
                FormDefinitionRecord.bot_instance_id == bot_id
            )
        ).all()
        names = {int(row[0]): str(row[1]) for row in definitions}
        action_rows = self._session.execute(
            select(
                UserAction.form_template_id,
                UserAction.action_type,
                func.count(UserAction.id),
                func.count(func.distinct(UserAction.user_id)),
            )
            .where(
                UserAction.bot_instance_id == bot_id,
                UserAction.form_template_id.isnot(None),
                UserAction.action_type.in_(
                    (
                        AnalyticsEventName.FORM_OPEN.value,
                        AnalyticsEventName.FORM_START.value,
                    )
                ),
                UserAction.created_at >= period.start,
                UserAction.created_at < period.end,
            )
            .group_by(UserAction.form_template_id, UserAction.action_type)
        ).all()
        actions: dict[int, dict[str, tuple[int, int]]] = defaultdict(dict)
        for form_id, action_type, total, unique in action_rows:
            actions[int(form_id)][str(action_type)] = (int(total), int(unique))
        submission_rows = self._session.execute(
            select(
                FormSubmission.form_template_id,
                func.count(FormSubmission.id),
                func.count(func.distinct(FormSubmission.user_id)),
                func.sum(case((FormSubmission.status == SubmissionStatusEnum.rejected, 1), else_=0)),
            )
            .where(
                FormSubmission.bot_instance_id == bot_id,
                FormSubmission.created_at >= period.start,
                FormSubmission.created_at < period.end,
            )
            .group_by(FormSubmission.form_template_id)
        ).all()
        submissions = {
            int(row[0]): (int(row[1]), int(row[2]), int(row[3] or 0)) for row in submission_rows
        }
        openers = self._form_users(
            select(UserAction.form_template_id, UserAction.user_id).where(
                UserAction.bot_instance_id == bot_id,
                UserAction.action_type == AnalyticsEventName.FORM_OPEN.value,
                UserAction.form_template_id.isnot(None),
                UserAction.created_at >= period.start,
                UserAction.created_at < period.end,
            )
        )
        submitters = self._form_users(
            select(FormSubmission.form_template_id, FormSubmission.user_id).where(
                FormSubmission.bot_instance_id == bot_id,
                FormSubmission.created_at >= period.start,
                FormSubmission.created_at < period.end,
            )
        )
        result: list[FormMetric] = []
        for form_id in set(names) | set(actions) | set(submissions):
            opens, _ = actions.get(form_id, {}).get(AnalyticsEventName.FORM_OPEN.value, (0, 0))
            form_openers = openers.get(form_id, set())
            completed = len(form_openers & submitters.get(form_id, set()))
            starts, _ = actions.get(form_id, {}).get(
                AnalyticsEventName.FORM_START.value, (0, 0)
            )
            total_submissions, unique_submitters, rejected = submissions.get(form_id, (0, 0, 0))
            if not (opens or starts or total_submissions):
                continue
            result.append(
                FormMetric(
                    form_id=form_id,
                    name=names.get(form_id, f"Форма #{form_id}"),
                    opens=opens,
                    starts=starts,
                    submissions=total_submissions,
                    unique_users=unique_submitters,
                    completion_rate=_ratio(completed, len(form_openers)),
                    rejected_share=_ratio(rejected, total_submissions),
                )
            )
        return tuple(sorted(result, key=lambda item: (-item.submissions, -item.opens, item.name)))

    def _form_users(self, statement: Any) -> dict[int, set[int]]:
        users: dict[int, set[int]] = defaultdict(set)
        for form_id, user_id in self._session.execute(statement.distinct()).all():
            users[int(form_id)].add(int(user_id))
        return users

    @staticmethod
    def _content_label(
        version: ContentVersionRecord,
        *,
        action_type: str,
        interaction_kind: str | None,
        block_id: str | None,
        item_id: str | None,
        tabs_block_id: str | None,
        tab_key: str | None,
        attachment_id: int | None,
    ) -> tuple[str, str | None]:
        blocks = list(_iter_blocks(version.blocks))
        if action_type == AnalyticsEventName.CONTENT_CATEGORY_OPEN.value:
            return version.title, None
        if action_type == AnalyticsEventName.CONTENT_TAB_OPEN.value:
            tabs = next((block for block in blocks if block.get("id") == tabs_block_id), None)
            if tabs is None:
                tabs = next(
                    (
                        block
                        for block in blocks
                        if block.get("type") == "tabs"
                        and any(item.get("key") == tab_key for item in block.get("tabs", []))
                    ),
                    None,
                )
            tab = next(
                (item for item in (tabs or {}).get("tabs", []) if item.get("key") == tab_key),
                None,
            )
            return str((tab or {}).get("title") or tab_key or "Вкладка"), None
        block = next((item for item in blocks if item.get("id") == block_id), None) or {}
        label = block.get("title") or interaction_kind or block_id or "Элемент"
        if interaction_kind == "accordion_item_open":
            item = next(
                (candidate for candidate in block.get("items", []) if candidate.get("id") == item_id),
                None,
            )
            label = (item or {}).get("title") or label
        elif interaction_kind == "file_download":
            item = next(
                (
                    candidate
                    for candidate in block.get("items", [])
                    if candidate.get("attachment_id") == attachment_id
                ),
                None,
            )
            label = (item or {}).get("title") or label
        target = None
        if block.get("type") == "form_action":
            target = f"Форма #{block.get('form_id')}"
        elif block.get("type") == "capability_action":
            target = f"{block.get('capability_key')} / {block.get('view_key')}"
        return str(label), target

    def _content(self, bot_id: int, period: DashboardPeriod) -> tuple[ContentMetric, ...]:
        rows = self._session.execute(
            select(
                UserAction.category_id,
                func.max(UserAction.content_version_id),
                UserAction.action_type,
                UserAction.interaction_kind,
                UserAction.block_id,
                UserAction.item_id,
                func.max(UserAction.tabs_block_id),
                UserAction.tab_key,
                UserAction.attachment_id,
                func.count(UserAction.id),
                func.count(func.distinct(UserAction.user_id)),
            )
            .where(
                UserAction.bot_instance_id == bot_id,
                UserAction.category_id.isnot(None),
                UserAction.content_version_id.isnot(None),
                UserAction.action_type.in_(CONTENT_ACTIONS),
                UserAction.created_at >= period.start,
                UserAction.created_at < period.end,
            )
            .group_by(
                UserAction.category_id,
                UserAction.action_type,
                UserAction.interaction_kind,
                UserAction.block_id,
                UserAction.item_id,
                UserAction.tab_key,
                UserAction.attachment_id,
            )
        ).all()
        version_ids = {int(row[1]) for row in rows}
        versions = {
            item.id: item
            for item in self._session.execute(
                select(ContentVersionRecord).where(ContentVersionRecord.id.in_(version_ids))
            ).scalars()
        } if version_ids else {}
        result: list[ContentMetric] = []
        for row in rows:
            version = versions.get(int(row[1]))
            if version is None:
                continue
            label, target = self._content_label(
                version,
                action_type=str(row[2]),
                interaction_kind=row[3],
                block_id=row[4],
                item_id=row[5],
                tabs_block_id=row[6],
                tab_key=row[7],
                attachment_id=row[8],
            )
            result.append(
                ContentMetric(
                    category_id=int(row[0]),
                    content_version_id=int(row[1]),
                    category_name=version.title,
                    kind=str(row[3] or row[2]),
                    block_id=row[4] or row[6],
                    item_id=row[5] or row[7],
                    label=label,
                    target_label=target,
                    total=int(row[9]),
                    unique_users=int(row[10]),
                )
            )
        return tuple(sorted(result, key=lambda item: (-item.total, item.category_name, item.label))[:100])

    def _capabilities(
        self,
        bot_id: int,
        period: DashboardPeriod,
    ) -> tuple[CapabilityMetric, ...]:
        rows = self._session.execute(
            select(
                UserAction.capability_key,
                UserAction.capability_view_key,
                func.sum(case((UserAction.action_type == AnalyticsEventName.CAPABILITY_VIEW_OPEN.value, 1), else_=0)),
                func.sum(case((UserAction.action_type == AnalyticsEventName.CAPABILITY_LOOKUP_COMPLETE.value, 1), else_=0)),
                func.sum(
                    case(
                        (
                            and_(
                                UserAction.action_type == AnalyticsEventName.CAPABILITY_LOOKUP_COMPLETE.value,
                                UserAction.outcome_code == "found",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(case((UserAction.action_type == AnalyticsEventName.CAPABILITY_SUBSCRIPTION_CHANGED.value, 1), else_=0)),
                func.count(func.distinct(UserAction.user_id)),
            )
            .where(
                UserAction.bot_instance_id == bot_id,
                UserAction.capability_key.isnot(None),
                UserAction.action_type.in_(CAPABILITY_ACTIONS),
                UserAction.created_at >= period.start,
                UserAction.created_at < period.end,
            )
            .group_by(UserAction.capability_key, UserAction.capability_view_key)
        ).all()
        return tuple(
            CapabilityMetric(
                capability_key=str(row[0]),
                view_key=row[1],
                opens=int(row[2] or 0),
                lookups=int(row[3] or 0),
                successful_lookups=int(row[4] or 0),
                subscription_changes=int(row[5] or 0),
                unique_users=int(row[6] or 0),
            )
            for row in rows
        )

    def _tickets_trend(
        self,
        bot_id: int,
        period: DashboardPeriod,
    ) -> tuple[TicketTrendPoint, ...]:
        day_column = _day(Message.created_at).label("day")
        rows = self._session.execute(
            select(
                day_column,
                func.count(func.distinct(case((Message.direction == MessageDirectionEnum.in_, Message.user_id)))),
                func.count(
                    func.distinct(
                        case(
                            (
                                and_(
                                    Message.direction == MessageDirectionEnum.out,
                                    Message.replied_by_admin_id.isnot(None)
                                    | Message.is_ai_answered.is_(True),
                                ),
                                Message.user_id,
                            )
                        )
                    )
                ),
            )
            .where(
                Message.bot_instance_id == bot_id,
                Message.created_at >= period.start,
                Message.created_at < period.end,
            )
            .group_by(day_column)
            .order_by(day_column)
        ).all()
        counts = {_row_day(row[0]): (int(row[1]), int(row[2])) for row in rows}
        return tuple(
            TicketTrendPoint(
                day=item,
                incoming=counts.get(item, (0, 0))[0],
                answered=counts.get(item, (0, 0))[1],
            )
            for item in _period_days(period)
        )

    def _campaign_link_totals(
        self,
        bot_ids: tuple[int, ...],
        period: DashboardPeriod,
    ) -> tuple[int, int]:
        if not bot_ids:
            return 0, 0
        total, unique = self._session.execute(
            select(
                func.count(CampaignLinkOpenRecord.id),
                func.count(func.distinct(CampaignLinkOpenRecord.bot_membership_id)),
            ).where(
                self._ids_filter(CampaignLinkOpenRecord.bot_instance_id, bot_ids),
                CampaignLinkOpenRecord.occurred_at >= period.start,
                CampaignLinkOpenRecord.occurred_at < period.end,
            )
        ).one()
        return int(total or 0), int(unique or 0)

    def _campaign_link_repeat_and_unmatched(
        self,
        bot_ids: tuple[int, ...],
        period: DashboardPeriod,
    ) -> tuple[int, int]:
        """Repeat opens are a lifetime sum (no per-open timestamps); unmatched opens are
        filtered by the period."""
        if not bot_ids:
            return 0, 0
        repeat_total = self._session.execute(
            select(func.coalesce(func.sum(CampaignLinkRecord.repeat_open_count), 0)).where(
                self._ids_filter(CampaignLinkRecord.bot_instance_id, bot_ids),
                CampaignLinkRecord.deleted_at.is_(None),
            )
        ).scalar()
        unmatched_total = self._session.execute(
            select(func.count(CampaignLinkUnmatchedOpenRecord.id)).where(
                self._ids_filter(CampaignLinkUnmatchedOpenRecord.bot_instance_id, bot_ids),
                CampaignLinkUnmatchedOpenRecord.occurred_at >= period.start,
                CampaignLinkUnmatchedOpenRecord.occurred_at < period.end,
            )
        ).scalar()
        return int(repeat_total or 0), int(unmatched_total or 0)

    def _campaign_links(
        self,
        bot_id: int,
        period: DashboardPeriod,
    ) -> tuple[CampaignLinkMetric, ...]:
        rows = self._session.execute(
            select(
                CampaignLinkRecord.id,
                CampaignLinkRecord.code,
                CampaignLinkRecord.campaign,
                CampaignLinkRecord.source,
                CampaignLinkRecord.placement,
                CampaignLinkRecord.target,
                func.count(CampaignLinkOpenRecord.id),
                func.count(func.distinct(CampaignLinkOpenRecord.bot_membership_id)),
            )
            .join(
                CampaignLinkOpenRecord,
                and_(
                    CampaignLinkOpenRecord.campaign_link_id == CampaignLinkRecord.id,
                    CampaignLinkOpenRecord.occurred_at >= period.start,
                    CampaignLinkOpenRecord.occurred_at < period.end,
                ),
            )
            .where(CampaignLinkRecord.bot_instance_id == bot_id)
            .group_by(
                CampaignLinkRecord.id,
                CampaignLinkRecord.code,
                CampaignLinkRecord.campaign,
                CampaignLinkRecord.source,
                CampaignLinkRecord.placement,
                CampaignLinkRecord.target,
            )
        ).all()
        return tuple(
            sorted(
                (
                    CampaignLinkMetric(
                        campaign_link_id=int(row[0]),
                        code=str(row[1]),
                        campaign=str(row[2]),
                        source=str(row[3]),
                        placement=str(row[4]),
                        target=str(row[5]),
                        opens=int(row[6]),
                        unique_opens=int(row[7]),
                    )
                    for row in rows
                ),
                key=lambda item: -item.opens,
            )
        )

    def get_bot_dashboard(
        self,
        bot_instance_id: int,
        period: DashboardPeriod,
        previous_period: DashboardPeriod,
    ) -> BotDashboard:
        return BotDashboard(
            generated_at=datetime.now(UTC),
            period=period,
            summary=self._bot_summary(bot_instance_id, period),
            previous_summary=self._bot_summary(bot_instance_id, previous_period),
            funnel=self._funnel(bot_instance_id, period),
            trend=self._bot_trend(bot_instance_id, period),
            forms=self._forms(bot_instance_id, period),
            content=self._content(bot_instance_id, period),
            capabilities=self._capabilities(bot_instance_id, period),
            tickets_trend=self._tickets_trend(bot_instance_id, period),
            campaign_links=self._campaign_links(bot_instance_id, period),
        )

    def _platform_summary(
        self,
        bot_ids: tuple[int, ...],
        period: DashboardPeriod,
    ) -> PlatformSummary:
        if not bot_ids:
            return PlatformSummary()
        activity = self._activity(bot_ids, period)
        active_users = self._session.execute(
            select(func.count(func.distinct(activity.c.user_id)))
        ).scalar()
        memberships = self._session.execute(
            select(
                func.count(BotMembershipRecord.id),
                func.count(func.distinct(BotMembershipRecord.user_id)),
            ).where(
                self._ids_filter(BotMembershipRecord.bot_instance_id, bot_ids),
                BotMembershipRecord.created_at >= period.start,
                BotMembershipRecord.created_at < period.end,
            )
        ).one()
        first_membership = (
            select(
                BotMembershipRecord.user_id,
                func.min(BotMembershipRecord.created_at).label("first_seen"),
            )
            .where(self._ids_filter(BotMembershipRecord.bot_instance_id, bot_ids))
            .group_by(BotMembershipRecord.user_id)
            .subquery()
        )
        new_people = self._session.execute(
            select(func.count()).select_from(first_membership).where(
                first_membership.c.first_seen >= period.start,
                first_membership.c.first_seen < period.end,
            )
        ).scalar()
        cross_bot = (
            select(activity.c.user_id)
            .group_by(activity.c.user_id)
            .having(func.count(func.distinct(activity.c.bot_id)) >= 2)
            .subquery()
        )
        cross_bot_users = self._session.execute(
            select(func.count()).select_from(cross_bot)
        ).scalar()
        submissions, submitters = self._session.execute(
            select(
                func.count(FormSubmission.id),
                func.count(func.distinct(FormSubmission.user_id)),
            ).where(
                self._ids_filter(FormSubmission.bot_instance_id, bot_ids),
                FormSubmission.created_at >= period.start,
                FormSubmission.created_at < period.end,
            )
        ).one()
        content_interactions, capability_uses = self._session.execute(
            select(
                func.sum(case((UserAction.action_type.in_(CONTENT_ACTIONS), 1), else_=0)),
                func.sum(case((UserAction.action_type.in_(CAPABILITY_ACTIONS), 1), else_=0)),
            ).where(
                self._ids_filter(UserAction.bot_instance_id, bot_ids),
                UserAction.created_at >= period.start,
                UserAction.created_at < period.end,
            )
        ).one()
        campaign_opens, campaign_unique_opens = self._campaign_link_totals(bot_ids, period)
        campaign_repeat_opens, campaign_unmatched_opens = self._campaign_link_repeat_and_unmatched(
            bot_ids, period
        )
        _, _, avg_new_to_done = self._workflow_averages(bot_ids, period)
        return PlatformSummary(
            bots=len(bot_ids),
            active_users=int(active_users or 0),
            new_people=int(new_people or 0),
            new_memberships=int(memberships[0] or 0),
            cross_bot_users=int(cross_bot_users or 0),
            submissions=int(submissions or 0),
            submitters=int(submitters or 0),
            conversion_rate=_ratio(int(submitters or 0), int(active_users or 0)),
            open_tickets=self._open_tickets(bot_ids, period.end),
            avg_response_seconds=self._avg_response_seconds(bot_ids, period),
            avg_new_to_done_seconds=avg_new_to_done,
            content_interactions=int(content_interactions or 0),
            capability_uses=int(capability_uses or 0),
            campaign_link_opens=campaign_opens,
            campaign_link_unique_opens=campaign_unique_opens,
            campaign_link_repeat_opens=campaign_repeat_opens,
            campaign_link_unmatched_opens=campaign_unmatched_opens,
        )

    def _platform_trend(
        self,
        bot_names: dict[int, str],
        period: DashboardPeriod,
    ) -> tuple[PlatformTrendPoint, ...]:
        bot_ids = tuple(bot_names)
        if not bot_ids:
            return ()
        activity = self._activity(bot_ids, period)
        activity_day = _day(activity.c.occurred_at).label("day")
        activity_rows = self._session.execute(
            select(
                activity.c.bot_id,
                activity_day,
                func.count(func.distinct(activity.c.user_id)),
            )
            .group_by(activity.c.bot_id, activity_day)
        ).all()
        submission_day = _day(FormSubmission.created_at).label("day")
        submission_rows = self._session.execute(
            select(
                FormSubmission.bot_instance_id,
                submission_day,
                func.count(FormSubmission.id),
            )
            .where(
                self._ids_filter(FormSubmission.bot_instance_id, bot_ids),
                FormSubmission.created_at >= period.start,
                FormSubmission.created_at < period.end,
            )
            .group_by(FormSubmission.bot_instance_id, submission_day)
        ).all()
        points: dict[tuple[int, date], list[int]] = {
            (bot_id, day_value): [0, 0] for bot_id in bot_ids for day_value in _period_days(period)
        }
        for bot_id, day_value, count in activity_rows:
            points.setdefault((int(bot_id), _row_day(day_value)), [0, 0])[0] = int(count)
        for bot_id, day_value, count in submission_rows:
            points.setdefault((int(bot_id), _row_day(day_value)), [0, 0])[1] = int(count)
        return tuple(
            PlatformTrendPoint(
                day=day_value,
                bot_id=bot_id,
                bot_name=bot_names[bot_id],
                active_users=values[0],
                submissions=values[1],
            )
            for (bot_id, day_value), values in sorted(points.items(), key=lambda item: (item[0][1], item[0][0]))
        )

    def get_platform_dashboard(
        self,
        period: DashboardPeriod,
        previous_period: DashboardPeriod,
        *,
        include_inactive: bool,
    ) -> PlatformDashboard:
        bot_query = (
            select(BotInstanceRecord)
            .where(BotInstanceRecord.deleted_at.is_(None))
            .order_by(BotInstanceRecord.order, BotInstanceRecord.id)
        )
        if not include_inactive:
            bot_query = bot_query.where(BotInstanceRecord.is_active.is_(True))
        bots = list(self._session.execute(bot_query).scalars())
        bot_ids = tuple(bot.id for bot in bots)
        comparisons = tuple(
            BotComparison(
                bot_id=bot.id,
                slug=bot.slug,
                name=bot.name,
                active_users=current.active_users,
                new_users=current.new_users,
                submissions=current.submissions,
                submitters=current.submitters,
                conversion_rate=current.conversion_rate,
                content_interactions=current.content_interactions,
                capability_uses=current.capability_uses,
                open_tickets=current.open_tickets,
                avg_response_seconds=current.avg_response_seconds,
                avg_new_to_done_seconds=current.avg_new_to_done_seconds,
                previous=previous,
                campaign_link_opens=current.campaign_link_opens,
                campaign_link_unique_opens=current.campaign_link_unique_opens,
                campaign_link_repeat_opens=current.campaign_link_repeat_opens,
                campaign_link_unmatched_opens=current.campaign_link_unmatched_opens,
            )
            for bot in bots
            for current, previous in [
                (self._bot_summary(bot.id, period), self._bot_summary(bot.id, previous_period))
            ]
        )
        return PlatformDashboard(
            generated_at=datetime.now(UTC),
            period=period,
            summary=self._platform_summary(bot_ids, period),
            previous_summary=self._platform_summary(bot_ids, previous_period),
            bots=comparisons,
            trend=self._platform_trend({bot.id: bot.name for bot in bots}, period),
        )
