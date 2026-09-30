"""Integration tests for `modules/analytics/presentation/stats_router.py`.

New coverage (Task 062) -- no test file exercised `GET /overview` before this migration. Follows
the real-Postgres-session pattern `test_tickets_http.py`/`test_users_admin_http.py` established,
since the window-function response-time query (`get_avg_response_seconds`) and the
`date_trunc`-grouped timeseries aren't reproducible against a fake session.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete

import app.main  # noqa: F401 -- registers every ORM class in Base.metadata by importing every
# router (needed when this file runs in isolation, same reasoning as test_tickets_http.py).
from app.api.deps import CurrentPrincipal, require_staff
from app.db.session import SessionLocal, get_db
from app.models.enums import MessageDirectionEnum, SubmissionStatusEnum, SystemEnum
from app.models.form import FormTemplate
from app.modules.analytics.presentation.stats_router import router
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.bot_instances.infrastructure.models import BotInstanceRecord
from app.modules.forms.infrastructure.models import FormSubmission, FormVersionRecord
from app.modules.profiles.infrastructure.models import BotMembershipRecord, User
from app.modules.support_chat.infrastructure.models import Message
from app.modules.tenancy.presentation.dependencies import require_tenant_access


class _Ctx:
    def __init__(self, db, bot: BotInstanceRecord) -> None:
        self.db = db
        self.bot = bot
        self.users: list[User] = []

    def make_user(self, *, bot: BotInstanceRecord | None = None) -> User:
        user = User(user_id=f"u-{uuid4().hex[:10]}", system=SystemEnum.max)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.db.add(
            BotMembershipRecord(bot_instance_id=(bot or self.bot).id, user_id=user.id, is_active=True)
        )
        self.db.commit()
        self.users.append(user)
        return user

    def form(self, *, name: str = "Test form", bot: BotInstanceRecord | None = None) -> FormTemplate:
        form = FormTemplate(bot_instance_id=(bot or self.bot).id, slug=f"f-{uuid4().hex[:8]}", name=name)
        self.db.add(form)
        self.db.commit()
        self.db.refresh(form)
        version = FormVersionRecord(
            form_definition_id=form.id,
            version=1,
            source_revision=0,
            name=name,
            fields=[],
            published_at=datetime.now(tz=UTC),
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        form._test_version_id = version.id  # not a mapped column; test-only bookkeeping
        return form

    def submission(
        self,
        *,
        form: FormTemplate,
        user: User,
        status: SubmissionStatusEnum = SubmissionStatusEnum.new,
        created_at: datetime | None = None,
        bot: BotInstanceRecord | None = None,
    ) -> FormSubmission:
        sub = FormSubmission(
            bot_instance_id=(bot or self.bot).id,
            form_template_id=form.id,
            form_version_id=form._test_version_id,
            user_id=user.id,
            values={},
            status=status,
            created_at=created_at or datetime.now(tz=UTC),
        )
        self.db.add(sub)
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def message(
        self,
        *,
        user: User,
        direction: MessageDirectionEnum,
        created_at: datetime | None = None,
        replied_by_admin_id: int | None = None,
        bot: BotInstanceRecord | None = None,
    ) -> Message:
        msg = Message(
            bot_instance_id=(bot or self.bot).id,
            user_id=user.id,
            system=SystemEnum.max,
            direction=direction,
            text="hi",
            replied_by_admin_id=replied_by_admin_id,
            created_at=created_at or datetime.now(tz=UTC),
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def app(self) -> FastAPI:
        app = FastAPI()
        app.include_router(router, prefix="/stats")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[require_tenant_access] = lambda: BotInstance(
            id=self.bot.id, slug=self.bot.slug, name=self.bot.name
        )
        app.dependency_overrides[require_staff] = lambda: CurrentPrincipal(
            sub="a:1", role="admin", system="max", user_id=None, admin_id=1
        )
        return app


@pytest.fixture
def ctx():
    db = SessionLocal()
    suffix = uuid4().hex[:10]
    bot = BotInstanceRecord(slug=f"test-stats-{suffix}", name="Test Stats Bot")
    db.add(bot)
    db.commit()
    db.refresh(bot)

    context = _Ctx(db, bot)
    try:
        yield context
    finally:
        db.rollback()
        # FormSubmission.bot_instance_id is ON DELETE RESTRICT (unlike Message/BotMembershipRecord/
        # form_templates, which cascade) -- must go first or deleting the bot below fails.
        db.execute(delete(FormSubmission).where(FormSubmission.bot_instance_id == bot.id))
        db.commit()
        db.delete(bot)  # cascades Message/BotMembershipRecord/form_templates/form_versions
        db.commit()
        for user in context.users:
            db.delete(user)
        db.commit()
        db.close()


def test_overview_counts_submissions_and_form_breakdown(ctx) -> None:
    user = ctx.make_user()
    form = ctx.form(name="Заявка на пропуск")
    ctx.submission(form=form, user=user)

    response = TestClient(ctx.app()).get("/stats/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["kpi"]["total_submissions"] == 1
    assert body["forms"]["all"] == [{"form_id": form.id, "name": form.name, "count": 1}]


def test_overview_actions_mode_unique_vs_all(ctx) -> None:
    from app.models.logger import UserAction

    user = ctx.make_user()
    for _ in range(2):
        action = UserAction(
            bot_instance_id=ctx.bot.id, user_id=user.id, action_type="content_view"
        )
        ctx.db.add(action)
    ctx.db.commit()

    all_body = TestClient(ctx.app()).get("/stats/overview", params={"action_mode": "all"}).json()
    unique_body = TestClient(ctx.app()).get(
        "/stats/overview", params={"action_mode": "unique"}
    ).json()

    all_item = next(i for i in all_body["actions"]["items"] if i["action_type"] == "content_view")
    unique_item = next(
        i for i in unique_body["actions"]["items"] if i["action_type"] == "content_view"
    )
    assert all_item["count"] == 2
    assert unique_item["count"] == 1


def test_overview_respects_explicit_date_range_over_default_window(ctx) -> None:
    user = ctx.make_user()
    form = ctx.form()
    old_at = datetime.now(tz=UTC) - timedelta(days=60)
    ctx.submission(form=form, user=user, created_at=old_at)

    default_window = TestClient(ctx.app()).get("/stats/overview").json()
    assert default_window["kpi"]["total_submissions"] == 0

    explicit_range = TestClient(ctx.app()).get(
        "/stats/overview",
        params={
            "date_from": (old_at - timedelta(days=1)).date().isoformat(),
            "date_to": (old_at + timedelta(days=1)).date().isoformat(),
        },
    ).json()
    assert explicit_range["kpi"]["total_submissions"] == 1


def test_overview_tickets_counts_open_ticket_and_response_time(ctx) -> None:
    user = ctx.make_user()
    incoming_at = datetime.now(tz=UTC) - timedelta(minutes=10)
    ctx.message(user=user, direction=MessageDirectionEnum.in_, created_at=incoming_at)
    ctx.message(
        user=user,
        direction=MessageDirectionEnum.out,
        created_at=incoming_at + timedelta(minutes=5),
        replied_by_admin_id=None,
    )

    body = TestClient(ctx.app()).get("/stats/overview").json()

    assert body["tickets"]["new"] == 1
    # no admin reply yet (replied_by_admin_id is None) -> still counted as open
    assert body["tickets"]["open"] == 1


def test_overview_excludes_data_from_other_bots(ctx) -> None:
    other_bot = BotInstanceRecord(slug=f"other-{uuid4().hex[:10]}", name="Other Bot")
    ctx.db.add(other_bot)
    ctx.db.commit()
    ctx.db.refresh(other_bot)
    try:
        other_user = ctx.make_user(bot=other_bot)
        other_form = ctx.form(bot=other_bot)
        ctx.submission(form=other_form, user=other_user, bot=other_bot)
        ctx.message(user=other_user, direction=MessageDirectionEnum.in_, bot=other_bot)

        body = TestClient(ctx.app()).get("/stats/overview").json()

        assert body["kpi"]["total_submissions"] == 0
        assert body["forms"]["all"] == []
        assert body["tickets"]["new"] == 0
    finally:
        ctx.db.execute(delete(FormSubmission).where(FormSubmission.bot_instance_id == other_bot.id))
        ctx.db.commit()
        ctx.db.delete(other_bot)
        ctx.db.commit()
