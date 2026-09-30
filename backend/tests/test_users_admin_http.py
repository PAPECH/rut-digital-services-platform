"""Integration tests for `modules/profiles/presentation/admin_router.py`.

New coverage (Task 061) -- no test file exercised `list_users`/`get_user`/`patch_ban` before this
migration. Follows the real-Postgres-session pattern `test_tickets_http.py` established, since
`list_users`' campaign-source enrichment and `get_user`'s three-way aggregation are direct
SQLAlchemy queries a hand-rolled fake session can't faithfully reproduce.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

import app.main  # noqa: F401 -- registers every ORM class (including modules not in the
# `app.models` barrel) in Base.metadata by importing every router.
from app.api.deps import CurrentPrincipal, require_admin, require_staff
from app.db.session import SessionLocal, get_db
from app.models.enums import AdminRoleEnum, MessageDirectionEnum, SubmissionStatusEnum, SystemEnum
from app.modules.admins.infrastructure.models import Admin
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.bot_instances.infrastructure.models import BotInstanceRecord
from app.modules.campaign_links.infrastructure.models import CampaignLinkRecord
from app.modules.forms.infrastructure.models import (
    FormDefinitionRecord,
    FormSubmission,
    FormVersionRecord,
)
from app.modules.profiles.infrastructure.models import BotMembershipRecord, User
from app.modules.profiles.presentation.admin_router import router
from app.modules.support_chat.infrastructure.models import Message
from app.modules.tenancy.presentation.dependencies import require_tenant_access


class _Ctx:
    def __init__(self, db, bot: BotInstanceRecord, admin: Admin) -> None:
        self.db = db
        self.bot = bot
        self.admin = admin
        self.users: list[User] = []

    def make_user(self, *, first_name: str = "Ivan", bot: BotInstanceRecord | None = None) -> User:
        user = User(user_id=f"u-{uuid4().hex[:10]}", system=SystemEnum.max, first_name=first_name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.db.add(
            BotMembershipRecord(
                bot_instance_id=(bot or self.bot).id, user_id=user.id, is_active=True
            )
        )
        self.db.commit()
        self.users.append(user)
        return user

    def campaign_link(self, **overrides) -> CampaignLinkRecord:
        link = CampaignLinkRecord(
            bot_instance_id=self.bot.id,
            code=overrides.get("code", f"c-{uuid4().hex[:8]}"),
            campaign=overrides.get("campaign", "spring"),
            source=overrides.get("source", "vk"),
            placement=overrides.get("placement", "story"),
            target=overrides.get("target", "app"),
        )
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def message(self, *, user_id: int, direction=MessageDirectionEnum.in_, text: str = "hi") -> Message:
        msg = Message(
            bot_instance_id=self.bot.id,
            user_id=user_id,
            system=SystemEnum.max,
            direction=direction,
            text=text,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def submission(self, *, user_id: int) -> FormSubmission:
        form = FormDefinitionRecord(
            bot_instance_id=self.bot.id,
            slug=f"form-{uuid4().hex[:8]}",
            name="Test form",
        )
        self.db.add(form)
        self.db.commit()
        self.db.refresh(form)

        version = FormVersionRecord(
            form_definition_id=form.id,
            version=1,
            source_revision=0,
            name="Test form",
            fields=[],
            published_at=datetime.now(tz=UTC),
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        sub = FormSubmission(
            bot_instance_id=self.bot.id,
            form_template_id=form.id,
            form_version_id=version.id,
            user_id=user_id,
            values={},
            form_snapshot={"name": "Test form"},
            status=SubmissionStatusEnum.new,
        )
        self.db.add(sub)
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def app(self, *, as_admin: bool = False) -> FastAPI:
        app = FastAPI()
        app.include_router(router, prefix="/users")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[require_tenant_access] = lambda: BotInstance(
            id=self.bot.id, slug=self.bot.slug, name=self.bot.name
        )
        principal = CurrentPrincipal(
            sub=f"a:{self.admin.id}", role="admin", system="max", user_id=None, admin_id=self.admin.id
        )
        app.dependency_overrides[require_staff] = lambda: principal
        if as_admin:
            app.dependency_overrides[require_admin] = lambda: principal
        return app


@pytest.fixture
def ctx():
    db = SessionLocal()
    suffix = uuid4().hex[:10]
    bot = BotInstanceRecord(slug=f"test-users-{suffix}", name="Test Users Bot")
    admin = Admin(
        max_user_id=f"admin-{suffix}", full_name="Test Admin", role=AdminRoleEnum.admin, is_active=True
    )
    db.add_all([bot, admin])
    db.commit()
    db.refresh(bot)
    db.refresh(admin)

    context = _Ctx(db, bot, admin)
    try:
        yield context
    finally:
        db.rollback()
        # FormSubmission.bot_instance_id is ON DELETE RESTRICT (unlike Message/BotMembershipRecord/
        # CampaignLinkRecord, which cascade) -- must go first or deleting the bot below fails.
        db.execute(delete(FormSubmission).where(FormSubmission.bot_instance_id == bot.id))
        db.commit()
        db.delete(bot)  # cascades Message/BotMembershipRecord/CampaignLinkRecord/form templates
        db.commit()
        for user in context.users:
            db.delete(user)
        db.delete(admin)
        db.commit()
        db.close()


def test_list_users_filters_by_query_and_system(ctx) -> None:
    zebra = ctx.make_user(first_name="Zebra")
    other = ctx.make_user(first_name="Другой")

    response = TestClient(ctx.app()).get("/users", params={"query": "Zebra"})

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [zebra.id]
    assert other.id not in [item["id"] for item in body]


def test_list_users_filters_by_system(ctx) -> None:
    max_user = ctx.make_user()
    beaver_user = User(user_id=f"u-{uuid4().hex[:10]}", system=SystemEnum.beavers)
    ctx.db.add(beaver_user)
    ctx.db.commit()
    ctx.db.refresh(beaver_user)
    ctx.db.add(BotMembershipRecord(bot_instance_id=ctx.bot.id, user_id=beaver_user.id, is_active=True))
    ctx.db.commit()
    ctx.users.append(beaver_user)

    response = TestClient(ctx.app()).get("/users", params={"system": "max"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert max_user.id in ids
    assert beaver_user.id not in ids


def test_list_users_enriches_campaign_source(ctx) -> None:
    user = ctx.make_user()
    link = ctx.campaign_link(code="spring-promo")
    membership = ctx.db.execute(
        select(BotMembershipRecord).where(
            BotMembershipRecord.bot_instance_id == ctx.bot.id,
            BotMembershipRecord.user_id == user.id,
        )
    ).scalar_one()
    membership.source_campaign_link_id = link.id
    ctx.db.commit()

    response = TestClient(ctx.app()).get("/users")

    assert response.status_code == 200
    body = response.json()
    row = next(item for item in body if item["id"] == user.id)
    assert row["campaign_source"]["code"] == "spring-promo"


def test_get_user_404_without_membership_in_resolved_bot(ctx) -> None:
    other_bot = BotInstanceRecord(slug=f"other-{uuid4().hex[:10]}", name="Other Bot")
    ctx.db.add(other_bot)
    ctx.db.commit()
    ctx.db.refresh(other_bot)
    try:
        stray = ctx.make_user(bot=other_bot)

        response = TestClient(ctx.app()).get(f"/users/{stray.id}")

        assert response.status_code == 404
    finally:
        ctx.db.delete(other_bot)
        ctx.db.commit()


def test_get_user_returns_profile_messages_and_submissions(ctx) -> None:
    user = ctx.make_user(first_name="Anna")
    ctx.message(user_id=user.id, text="hello")
    ctx.submission(user_id=user.id)

    response = TestClient(ctx.app()).get(f"/users/{user.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == user.id
    assert len(body["messages"]) == 1
    assert body["messages"][0]["text"] == "hello"
    assert len(body["submissions"]) == 1


def test_patch_ban_partial_update_leaves_other_fields_untouched(ctx) -> None:
    user = ctx.make_user()
    client = TestClient(ctx.app(as_admin=True))

    first = client.patch(
        f"/users/{user.id}/ban", json={"ban_chat": True, "ban_chat_reason": "spam"}
    )
    assert first.status_code == 200
    assert first.json()["ban_chat"] is True
    assert first.json()["ban_forms"] is False

    second = client.patch(f"/users/{user.id}/ban", json={"ban_forms": True})
    assert second.status_code == 200
    assert second.json()["ban_chat"] is True  # unset field untouched by exclude_unset
    assert second.json()["ban_forms"] is True


def test_patch_ban_rejects_self_ban(ctx) -> None:
    shadow_user = User(user_id=ctx.admin.max_user_id, system=SystemEnum.max)
    ctx.db.add(shadow_user)
    ctx.db.commit()
    ctx.db.refresh(shadow_user)
    ctx.db.add(BotMembershipRecord(bot_instance_id=ctx.bot.id, user_id=shadow_user.id, is_active=True))
    ctx.db.commit()
    ctx.users.append(shadow_user)

    response = TestClient(ctx.app(as_admin=True)).patch(
        f"/users/{shadow_user.id}/ban", json={"ban_chat": True}
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "self_ban_forbidden"


def test_patch_ban_404_for_user_outside_bot(ctx) -> None:
    other_bot = BotInstanceRecord(slug=f"other-{uuid4().hex[:10]}", name="Other Bot")
    ctx.db.add(other_bot)
    ctx.db.commit()
    ctx.db.refresh(other_bot)
    try:
        stray = ctx.make_user(bot=other_bot)

        response = TestClient(ctx.app(as_admin=True)).patch(
            f"/users/{stray.id}/ban", json={"ban_chat": True}
        )

        assert response.status_code == 404
    finally:
        ctx.db.delete(other_bot)
        ctx.db.commit()
