"""Integration tests for `modules/support_chat/presentation/tickets_router.py`.

`list_conversations`/`tickets_overview` are built from real subqueries and joins
(open/closed derivation, favorites aliasing) that a hand-rolled fake session can't
faithfully reproduce, so this file runs them against a real Postgres session instead
of the fake-repository pattern used elsewhere in this suite -- the first test file in
this repo to do so. Every row it creates is scoped under one throwaway bot and torn
down at the end of each test.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main  # noqa: F401 -- registers every ORM class (including modules not in the
# `app.models` barrel, e.g. campaign_links) in Base.metadata by importing every router.
# Needed when this file runs in isolation: SQLAlchemy resolves BotMembershipRecord's FK to
# campaign_links at flush time, and nothing else this file imports pulls that module in.
from app.api.deps import CurrentPrincipal, require_staff
from app.db.session import SessionLocal, get_db
from app.models.enums import AdminRoleEnum, MessageDirectionEnum, SystemEnum
from app.modules.admins.infrastructure.models import Admin
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.bot_instances.infrastructure.models import BotInstanceRecord
from app.modules.knowledge_base.domain.entities import MessageAiClassificationEnum
from app.modules.profiles.infrastructure.models import BotMembershipRecord, User
from app.modules.support_chat.infrastructure.models import Message, StaffFavorite
from app.modules.support_chat.presentation.tickets_router import router
from app.modules.tenancy.presentation.dependencies import require_tenant_access


class _Ctx:
    def __init__(self, db, bot: BotInstanceRecord, admin: Admin) -> None:
        self.db = db
        self.bot = bot
        self.admin = admin
        self.users: list[User] = []

    def make_user(self, *, first_name: str = "Ivan") -> User:
        user = User(user_id=f"u-{uuid4().hex[:10]}", system=SystemEnum.max, first_name=first_name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.db.add(BotMembershipRecord(bot_instance_id=self.bot.id, user_id=user.id, is_active=True))
        self.db.commit()
        self.users.append(user)
        return user

    def message(
        self,
        *,
        user_id: int,
        direction: MessageDirectionEnum,
        at: datetime,
        classification=None,
    ) -> Message:
        msg = Message(
            bot_instance_id=self.bot.id,
            user_id=user_id,
            system=SystemEnum.max,
            direction=direction,
            text="hi",
            ai_classification=classification,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        msg.created_at = at
        self.db.commit()
        return msg

    def app(self) -> FastAPI:
        app = FastAPI()
        app.include_router(router, prefix="/tickets")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[require_tenant_access] = lambda: BotInstance(
            id=self.bot.id, slug=self.bot.slug, name=self.bot.name
        )
        app.dependency_overrides[require_staff] = lambda: CurrentPrincipal(
            sub=f"a:{self.admin.id}", role="admin", system="max", user_id=None, admin_id=self.admin.id
        )
        return app


@pytest.fixture
def ctx():
    db = SessionLocal()
    suffix = uuid4().hex[:10]
    bot = BotInstanceRecord(slug=f"test-tickets-{suffix}", name="Test Tickets Bot")
    admin = Admin(
        max_user_id=f"admin-{suffix}", full_name="Test Support", role=AdminRoleEnum.admin, is_active=True
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
        db.delete(bot)  # cascades Message/StaffFavorite/BotMembershipRecord
        db.commit()
        for user in context.users:
            db.delete(user)
        db.delete(admin)
        db.commit()
        db.close()


def test_tickets_overview_counts_only_open_tickets(ctx) -> None:
    open_user = ctx.make_user(first_name="Open")
    closed_user = ctx.make_user(first_name="Closed")
    now = datetime.now(tz=UTC)
    ctx.message(user_id=open_user.id, direction=MessageDirectionEnum.in_, at=now)
    ctx.message(
        user_id=closed_user.id, direction=MessageDirectionEnum.in_, at=now - timedelta(minutes=5)
    )
    ctx.message(user_id=closed_user.id, direction=MessageDirectionEnum.out, at=now)

    response = TestClient(ctx.app()).get("/tickets/overview")

    assert response.status_code == 200
    assert response.json() == {"open_count": 1, "unread_count": 1}


def test_list_conversations_only_open_filters_closed_tickets(ctx) -> None:
    open_user = ctx.make_user(first_name="Open")
    closed_user = ctx.make_user(first_name="Closed")
    now = datetime.now(tz=UTC)
    ctx.message(user_id=open_user.id, direction=MessageDirectionEnum.in_, at=now)
    ctx.message(
        user_id=closed_user.id, direction=MessageDirectionEnum.in_, at=now - timedelta(minutes=5)
    )
    ctx.message(user_id=closed_user.id, direction=MessageDirectionEnum.out, at=now)

    response = TestClient(ctx.app()).get("/tickets/conversations", params={"only_open": True})

    assert response.status_code == 200
    body = response.json()
    assert [item["user_id"] for item in body] == [open_user.id]
    assert body[0]["has_open_ticket"] is True


def test_list_conversations_marks_staff_requested(ctx) -> None:
    user = ctx.make_user()
    ctx.message(
        user_id=user.id,
        direction=MessageDirectionEnum.in_,
        at=datetime.now(tz=UTC),
        classification=MessageAiClassificationEnum.kb_staff_requested,
    )

    response = TestClient(ctx.app()).get("/tickets/conversations")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["staff_requested"] is True


def test_list_conversations_query_filters_by_name(ctx) -> None:
    target = ctx.make_user(first_name="Zebra")
    other = ctx.make_user(first_name="Другой")
    now = datetime.now(tz=UTC)
    ctx.message(user_id=target.id, direction=MessageDirectionEnum.in_, at=now)
    ctx.message(user_id=other.id, direction=MessageDirectionEnum.in_, at=now)

    response = TestClient(ctx.app()).get("/tickets/conversations", params={"query": "Zebra"})

    assert response.status_code == 200
    body = response.json()
    assert [item["user_id"] for item in body] == [target.id]


def test_set_favorite_add_is_idempotent_then_removable(ctx) -> None:
    user = ctx.make_user()
    client = TestClient(ctx.app())

    first = client.post("/tickets/favorites", json={"user_id": user.id, "is_favorite": True})
    second = client.post("/tickets/favorites", json={"user_id": user.id, "is_favorite": True})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["is_favorite"] is True
    assert second.json()["is_favorite"] is True

    removed = client.post("/tickets/favorites", json={"user_id": user.id, "is_favorite": False})
    assert removed.status_code == 200
    assert removed.json()["is_favorite"] is False


def test_set_favorite_rejects_user_outside_bot(ctx) -> None:
    stray = User(user_id=f"stray-{uuid4().hex[:8]}", system=SystemEnum.max)
    ctx.db.add(stray)
    ctx.db.commit()
    ctx.db.refresh(stray)
    try:
        response = TestClient(ctx.app()).post(
            "/tickets/favorites", json={"user_id": stray.id, "is_favorite": True}
        )
        assert response.status_code == 404
    finally:
        ctx.db.delete(stray)
        ctx.db.commit()


def test_get_admins_ticket_lists_favoriting_admin_names(ctx) -> None:
    user = ctx.make_user()
    ctx.db.add(StaffFavorite(bot_instance_id=ctx.bot.id, user_id=user.id, support_id=ctx.admin.id))
    ctx.db.commit()

    response = TestClient(ctx.app()).get("/tickets/admins", params={"user_id": user.id})

    assert response.status_code == 200
    assert response.json() == [ctx.admin.full_name]
