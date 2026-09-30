"""Dashboard figures computed against a real PostgreSQL session.

Every expected value below is derived by hand from the seeded rows, so a change in any
aggregate shows up as a concrete number mismatch. All rows live inside one transaction that is
rolled back after the test.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

import app.main  # noqa: F401
from app.db.session import SessionLocal
from app.models.enums import AdminRoleEnum, MessageDirectionEnum, SubmissionStatusEnum, SystemEnum
from app.models.logger import UserAction
from app.modules.admins.infrastructure.models import Admin
from app.modules.analytics.application.dashboard_use_cases import resolve_period
from app.modules.analytics.domain.events import AnalyticsEventName
from app.modules.analytics.infrastructure.dashboard_repository import SqlAlchemyDashboardRepository
from app.modules.bot_instances.infrastructure.models import BotInstanceRecord
from app.modules.forms.infrastructure.models import (
    FormDefinitionRecord,
    FormSubmission,
    FormVersionRecord,
    SubmissionStatusHistory,
)
from app.modules.profiles.infrastructure.models import BotMembershipRecord, User
from app.modules.support_chat.infrastructure.models import Message

MSK = ZoneInfo("Europe/Moscow")
HOUR = 3600


def at(day: int, hour: int, minute: int = 0, *, month: int = 9) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=MSK)


class Seed:
    def __init__(self, db) -> None:
        self.db = db
        self.admin = Admin(
            max_user_id=f"dash-{uuid4().hex[:8]}",
            full_name="Staff",
            role=AdminRoleEnum.admin,
            is_active=True,
        )
        db.add(self.admin)
        db.flush()

    def bot(self, *, deleted: bool = False) -> BotInstanceRecord:
        bot = BotInstanceRecord(slug=f"dash-{uuid4().hex[:8]}", name="Dash bot")
        if deleted:
            bot.is_active = False
            bot.deleted_at = at(1, 9)
        self.db.add(bot)
        self.db.flush()
        return bot

    def user(self, bot: BotInstanceRecord, joined: datetime) -> User:
        user = User(user_id=f"u-{uuid4().hex[:10]}", system=SystemEnum.max, first_name="U")
        self.db.add(user)
        self.db.flush()
        self.membership(bot, user, joined)
        return user

    def membership(self, bot: BotInstanceRecord, user: User, joined: datetime) -> None:
        self.db.add(
            BotMembershipRecord(
                bot_instance_id=bot.id, user_id=user.id, is_active=True, created_at=joined
            )
        )
        self.db.flush()

    def form(self, bot: BotInstanceRecord) -> tuple[FormDefinitionRecord, FormVersionRecord]:
        definition = FormDefinitionRecord(
            bot_instance_id=bot.id, slug=f"f-{uuid4().hex[:8]}", name="Справка", is_active=True
        )
        self.db.add(definition)
        self.db.flush()
        version = FormVersionRecord(
            form_definition_id=definition.id,
            version=1,
            source_revision=0,
            name="Справка",
            fields=[],
            published_at=at(1, 9),
        )
        self.db.add(version)
        self.db.flush()
        return definition, version

    def submission(
        self,
        bot: BotInstanceRecord,
        form: tuple[FormDefinitionRecord, FormVersionRecord],
        user: User,
        created: datetime,
        *,
        in_work: datetime | None = None,
        done: datetime | None = None,
        rejected: datetime | None = None,
    ) -> FormSubmission:
        status = SubmissionStatusEnum.new
        if in_work:
            status = SubmissionStatusEnum.in_work
        if done:
            status = SubmissionStatusEnum.done
        if rejected:
            status = SubmissionStatusEnum.rejected
        sub = FormSubmission(
            bot_instance_id=bot.id,
            form_template_id=form[0].id,
            form_version_id=form[1].id,
            user_id=user.id,
            values={},
            status=status,
            created_at=created,
        )
        self.db.add(sub)
        self.db.flush()
        previous = SubmissionStatusEnum.new
        for target, moment in (
            (SubmissionStatusEnum.in_work, in_work),
            (SubmissionStatusEnum.done, done),
            (SubmissionStatusEnum.rejected, rejected),
        ):
            if moment is None:
                continue
            self.db.add(
                SubmissionStatusHistory(
                    submission_id=sub.id,
                    from_status=previous,
                    to_status=target,
                    changed_at=moment,
                )
            )
            previous = target
        self.db.flush()
        return sub

    def message(
        self,
        bot: BotInstanceRecord,
        user: User,
        direction: MessageDirectionEnum,
        moment: datetime,
        *,
        staff: bool = False,
        ai: bool = False,
    ) -> None:
        self.db.add(
            Message(
                bot_instance_id=bot.id,
                user_id=user.id,
                system=SystemEnum.max,
                direction=direction,
                text="t",
                is_ai_answered=ai,
                replied_by_admin_id=self.admin.id if staff else None,
                created_at=moment,
            )
        )
        self.db.flush()

    def action(
        self,
        bot: BotInstanceRecord,
        user: User,
        name: AnalyticsEventName,
        moment: datetime,
        *,
        form_id: int | None = None,
    ) -> None:
        self.db.add(
            UserAction(
                bot_instance_id=bot.id,
                user_id=user.id,
                action_type=name.value,
                form_template_id=form_id,
                created_at=moment,
            )
        )
        self.db.flush()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def world(db):
    seed = Seed(db)
    bot = seed.bot()
    other = seed.bot()
    trashed = seed.bot(deleted=True)
    form = seed.form(bot)
    other_form = seed.form(other)

    u1 = seed.user(bot, at(2, 9))
    u2 = seed.user(bot, at(2, 9))
    u3 = seed.user(bot, at(25, 9, month=8))

    seed.submission(bot, form, u1, at(2, 10), in_work=at(2, 11), done=at(2, 13))
    seed.submission(bot, form, u1, at(3, 10), in_work=at(3, 10, 30), done=at(4, 10, 30))
    seed.submission(bot, form, u2, at(5, 10), in_work=at(5, 12))
    seed.submission(bot, form, u2, at(5, 11), rejected=at(5, 12))
    seed.submission(bot, form, u3, at(25, 10, month=8), in_work=at(25, 11, month=8), done=at(25, 12, month=8))

    seed.action(bot, u1, AnalyticsEventName.FORM_OPEN, at(2, 9, 55), form_id=form[0].id)
    seed.action(bot, u3, AnalyticsEventName.FORM_OPEN, at(6, 9), form_id=form[0].id)

    # u1: two questions, then a staff reply 40 minutes after the first one.
    seed.message(bot, u1, MessageDirectionEnum.in_, at(6, 10))
    seed.message(bot, u1, MessageDirectionEnum.in_, at(6, 10, 10))
    seed.message(bot, u1, MessageDirectionEnum.out, at(6, 10, 40), staff=True)
    # u2: knowledge base answered automatically.
    seed.message(bot, u2, MessageDirectionEnum.in_, at(7, 9), ai=True)
    seed.message(bot, u2, MessageDirectionEnum.out, datetime(2026, 9, 7, 9, 0, 5, tzinfo=MSK), ai=True)
    # u3: still waiting.
    seed.message(bot, u3, MessageDirectionEnum.in_, at(8, 10))

    ov = seed.user(other, at(2, 9))
    seed.submission(other, other_form, ov, at(3, 10), in_work=at(3, 10, 1), done=at(3, 10, 2))
    seed.message(other, ov, MessageDirectionEnum.in_, at(3, 10))
    seed.action(other, ov, AnalyticsEventName.FORM_OPEN, at(3, 9), form_id=other_form[0].id)

    period, previous = resolve_period(days=30, date_from=date(2026, 9, 1), date_to=date(2026, 9, 10))
    return {
        "repo": SqlAlchemyDashboardRepository(db),
        "bot": bot,
        "other": other,
        "trashed": trashed,
        "form": form,
        "period": period,
        "previous": previous,
    }


def test_bot_summary_figures(world) -> None:
    dashboard = world["repo"].get_bot_dashboard(world["bot"].id, world["period"], world["previous"])
    summary = dashboard.summary

    assert summary.active_users == 3
    assert summary.new_users == 2
    assert summary.submissions == 4
    assert summary.submitters == 2
    assert summary.conversion_rate == pytest.approx(2 / 3)
    assert summary.open_tickets == 1
    assert summary.avg_response_seconds == 40 * 60
    assert summary.ai_answers == 1
    assert summary.avg_new_to_work_seconds == (HOUR + HOUR // 2 + 2 * HOUR) // 3
    assert summary.avg_work_to_done_seconds == (2 * HOUR + 24 * HOUR) // 2
    assert summary.avg_new_to_done_seconds == (3 * HOUR + 24 * HOUR + HOUR // 2) // 2


def test_previous_period_figures(world) -> None:
    previous = world["repo"].get_bot_dashboard(
        world["bot"].id, world["period"], world["previous"]
    ).previous_summary

    assert previous.submissions == 1
    assert previous.new_users == 1
    assert previous.avg_new_to_done_seconds == 2 * HOUR
    assert previous.open_tickets == 0


def test_forms_completion_counts_only_openers_who_submitted(world) -> None:
    forms = world["repo"].get_bot_dashboard(world["bot"].id, world["period"], world["previous"]).forms

    assert len(forms) == 1
    metric = forms[0]
    assert (metric.opens, metric.submissions, metric.unique_users) == (2, 4, 2)
    assert metric.completion_rate == pytest.approx(0.5)
    assert metric.rejected_share == pytest.approx(0.25)


def test_trends_cover_every_day_of_the_period(world) -> None:
    dashboard = world["repo"].get_bot_dashboard(world["bot"].id, world["period"], world["previous"])

    assert [point.day for point in dashboard.trend] == [date(2026, 9, d) for d in range(1, 11)]
    by_day = {point.day: point for point in dashboard.trend}
    assert by_day[date(2026, 9, 5)].submissions == 2
    assert by_day[date(2026, 9, 1)].submissions == 0

    tickets = {point.day: point for point in dashboard.tickets_trend}
    assert len(tickets) == 10
    assert (tickets[date(2026, 9, 6)].incoming, tickets[date(2026, 9, 6)].answered) == (1, 1)
    assert (tickets[date(2026, 9, 7)].incoming, tickets[date(2026, 9, 7)].answered) == (1, 1)
    assert (tickets[date(2026, 9, 8)].incoming, tickets[date(2026, 9, 8)].answered) == (1, 0)


def test_other_bot_data_never_leaks_into_bot_view(world) -> None:
    dashboard = world["repo"].get_bot_dashboard(world["bot"].id, world["period"], world["previous"])

    assert dashboard.summary.submissions == 4
    assert all(item.form_id == world["form"][0].id for item in dashboard.forms)


def test_platform_view_aggregates_and_skips_deleted_bots(world) -> None:
    repo = world["repo"]
    bot_ids = (world["bot"].id, world["other"].id)

    summary = repo._platform_summary(bot_ids, world["period"])
    assert summary.submissions == 5
    assert summary.active_users == 4
    assert summary.open_tickets == 2
    assert summary.avg_new_to_done_seconds == (3 * HOUR + 24 * HOUR + HOUR // 2 + 120) // 3

    dashboard = repo.get_platform_dashboard(world["period"], world["previous"], include_inactive=True)
    compared = {item.bot_id: item for item in dashboard.bots}
    assert world["trashed"].id not in compared
    assert compared[world["bot"].id].avg_new_to_done_seconds == summary_bot_done(repo, world)


def summary_bot_done(repo, world) -> int:
    return repo.get_bot_dashboard(
        world["bot"].id, world["period"], world["previous"]
    ).summary.avg_new_to_done_seconds


def test_dashboard_endpoints_serialize_new_metric(world, db) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.deps import CurrentPrincipal, get_current_principal
    from app.db.session import get_db
    from app.modules.analytics.presentation.router import router
    from app.modules.bot_instances.domain.entities import BotInstance
    from app.modules.tenancy.presentation.dependencies import require_tenant_access

    bot = world["bot"]
    api = FastAPI()
    api.include_router(router, prefix="/analytics")
    api.dependency_overrides[get_db] = lambda: db
    api.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        sub="a:1", role="platform_admin", system="max", user_id=None, admin_id=1
    )
    api.dependency_overrides[require_tenant_access] = lambda: BotInstance(
        id=bot.id, slug=bot.slug, name=bot.name
    )
    client = TestClient(api)
    query = "date_from=2026-09-01&date_to=2026-09-10"

    bot_view = client.get(f"/analytics/dashboard/bot?{query}")
    platform_view = client.get(f"/analytics/dashboard/platform?{query}")

    assert bot_view.status_code == 200
    assert bot_view.json()["summary"]["avg_new_to_done_seconds"] == (27 * HOUR + HOUR // 2) // 2
    assert platform_view.status_code == 200
    row = next(item for item in platform_view.json()["bots"] if item["bot_id"] == bot.id)
    assert row["avg_new_to_done_seconds"] == (27 * HOUR + HOUR // 2) // 2
    assert "avg_new_to_done_seconds" in platform_view.json()["summary"]
