"""Integration tests for `modules/forms/presentation/submissions_router.py`.

New coverage (Task 063) -- no test file exercised `list_submissions`/`get_submission`/
`create_submission`/`patch_status` before this migration (the existing
`test_submission_attachments.py` only covers the two attachment endpoints, through a fake session,
and needs no changes here). Follows the real-Postgres-session pattern
`test_tickets_http.py`/`test_users_admin_http.py`/`test_stats_http.py` established.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete

import app.main  # noqa: F401 -- registers every ORM class in Base.metadata by importing every
# router (needed when this file runs in isolation, same reasoning as test_tickets_http.py).
from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import SessionLocal, get_db
from app.models.enums import SubmissionStatusEnum, SystemEnum
from app.modules.admins.infrastructure.models import Admin
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.bot_instances.infrastructure.models import AdminBotAccessRecord, BotInstanceRecord
from app.modules.forms.infrastructure.models import (
    FormDefinitionRecord,
    FormSubmission,
    FormVersionRecord,
)
from app.modules.forms.presentation.submissions_router import router
from app.modules.profiles.infrastructure.models import BotMembershipRecord, User
from app.modules.tenancy.presentation.dependencies import require_tenant_access

STUDENT_ROLE = "student"
STAFF_ROLE = "employee"


class _Ctx:
    def __init__(self, db, bot: BotInstanceRecord) -> None:
        self.db = db
        self.bot = bot
        self.users: list[User] = []
        self.admins: list[Admin] = []

    def make_student(
        self, *, complete_profile: bool = True, bot: BotInstanceRecord | None = None
    ) -> User:
        user = User(
            user_id=f"u-{uuid4().hex[:10]}",
            system=SystemEnum.max,
            first_name="Ivan" if complete_profile else None,
            last_name="Ivanov" if complete_profile else None,
            patronymic="Ivanovich" if complete_profile else None,
            phone="+79990000000" if complete_profile else None,
            phone_verified=complete_profile,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.db.add(
            BotMembershipRecord(bot_instance_id=(bot or self.bot).id, user_id=user.id, is_active=True)
        )
        self.db.commit()
        self.users.append(user)
        return user

    def membership_of(self, user: User, *, bot: BotInstanceRecord | None = None) -> BotMembershipRecord:
        from sqlalchemy import select

        return self.db.execute(
            select(BotMembershipRecord).where(
                BotMembershipRecord.bot_instance_id == (bot or self.bot).id,
                BotMembershipRecord.user_id == user.id,
            )
        ).scalar_one()

    def staff(self, *, can_process_submissions: bool = True) -> tuple[Admin, CurrentPrincipal]:
        admin = Admin(max_user_id=f"admin-{uuid4().hex[:10]}", full_name="Test Staff")
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        self.db.add(
            AdminBotAccessRecord(
                admin_id=admin.id,
                bot_instance_id=self.bot.id,
                can_process_submissions=can_process_submissions,
            )
        )
        self.db.commit()
        self.admins.append(admin)
        principal = CurrentPrincipal(
            sub=f"a:{admin.id}", role=STAFF_ROLE, system="max", user_id=None, admin_id=admin.id
        )
        return admin, principal

    def form(
        self,
        *,
        fields: list[dict] | None = None,
        is_active: bool = True,
        is_archived: bool = False,
        reply_on_accept: str | None = None,
        bot: BotInstanceRecord | None = None,
    ) -> tuple[FormDefinitionRecord, FormVersionRecord]:
        target_bot = bot or self.bot
        definition = FormDefinitionRecord(
            bot_instance_id=target_bot.id,
            slug=f"f-{uuid4().hex[:8]}",
            name="Test form",
            is_active=is_active,
            is_archived=is_archived,
        )
        self.db.add(definition)
        self.db.commit()
        self.db.refresh(definition)
        version = FormVersionRecord(
            form_definition_id=definition.id,
            version=1,
            source_revision=0,
            name="Test form",
            fields=fields or [],
            reply_on_accept=reply_on_accept,
            published_at=datetime.now(tz=UTC),
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        definition.published_version_id = version.id
        self.db.commit()
        self.db.refresh(definition)
        return definition, version

    def submission(
        self,
        *,
        definition: FormDefinitionRecord,
        version: FormVersionRecord,
        user: User,
        status: SubmissionStatusEnum = SubmissionStatusEnum.new,
        created_at: datetime | None = None,
        bot: BotInstanceRecord | None = None,
    ) -> FormSubmission:
        sub = FormSubmission(
            bot_instance_id=(bot or self.bot).id,
            form_template_id=definition.id,
            form_version_id=version.id,
            user_id=user.id,
            values={},
            status=status,
            created_at=created_at or datetime.now(tz=UTC),
        )
        self.db.add(sub)
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def app(self, principal: CurrentPrincipal, *, bot: BotInstanceRecord | None = None) -> FastAPI:
        target_bot = bot or self.bot
        app = FastAPI()
        app.include_router(router, prefix="/submissions")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[require_tenant_access] = lambda: BotInstance(
            id=target_bot.id, slug=target_bot.slug, name=target_bot.name
        )
        app.dependency_overrides[get_current_principal] = lambda: principal
        return app

    def student_principal(self, user: User) -> CurrentPrincipal:
        return CurrentPrincipal(
            sub=f"u:{user.id}", role=STUDENT_ROLE, system="max", user_id=user.id, admin_id=None
        )


@pytest.fixture
def ctx():
    db = SessionLocal()
    suffix = uuid4().hex[:10]
    bot = BotInstanceRecord(slug=f"test-submissions-{suffix}", name="Test Submissions Bot")
    db.add(bot)
    db.commit()
    db.refresh(bot)

    context = _Ctx(db, bot)
    try:
        yield context
    finally:
        db.rollback()
        # FormSubmission.bot_instance_id is ON DELETE RESTRICT (unlike BotMembershipRecord/
        # form_templates, which cascade) -- must go first or deleting the bot below fails.
        db.execute(delete(FormSubmission).where(FormSubmission.bot_instance_id == bot.id))
        db.commit()
        db.delete(bot)  # cascades BotMembershipRecord/AdminBotAccessRecord/form_templates/versions
        db.commit()
        for user in context.users:
            db.delete(user)
        for admin in context.admins:
            db.delete(admin)
        db.commit()
        db.close()


def test_list_submissions_student_sees_only_own(ctx) -> None:
    definition, version = ctx.form()
    mine = ctx.make_student()
    other = ctx.make_student()
    ctx.submission(definition=definition, version=version, user=mine)
    ctx.submission(definition=definition, version=version, user=other)

    response = TestClient(ctx.app(ctx.student_principal(mine))).get("/submissions")

    assert response.status_code == 200
    body = response.json()
    assert [item["user_id"] for item in body] == [mine.id]


def test_list_submissions_staff_filters_by_status(ctx) -> None:
    definition, version = ctx.form()
    student = ctx.make_student()
    ctx.submission(definition=definition, version=version, user=student, status=SubmissionStatusEnum.new)
    ctx.submission(
        definition=definition, version=version, user=student, status=SubmissionStatusEnum.done
    )
    _, staff_principal = ctx.staff()

    response = TestClient(ctx.app(staff_principal)).get(
        "/submissions", params={"status": "done"}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "done"


def test_get_submission_forbidden_for_another_students_submission(ctx) -> None:
    definition, version = ctx.form()
    owner = ctx.make_student()
    other = ctx.make_student()
    sub = ctx.submission(definition=definition, version=version, user=owner)

    response = TestClient(ctx.app(ctx.student_principal(other))).get(f"/submissions/{sub.id}")

    assert response.status_code == 403


def test_get_submission_404_for_submission_in_another_bot(ctx) -> None:
    other_bot = BotInstanceRecord(slug=f"other-{uuid4().hex[:10]}", name="Other Bot")
    ctx.db.add(other_bot)
    ctx.db.commit()
    ctx.db.refresh(other_bot)
    try:
        definition, version = ctx.form(bot=other_bot)
        stray_user = ctx.make_student(bot=other_bot)
        sub = ctx.submission(definition=definition, version=version, user=stray_user, bot=other_bot)
        _, staff_principal = ctx.staff()

        response = TestClient(ctx.app(staff_principal)).get(f"/submissions/{sub.id}")

        assert response.status_code == 404
    finally:
        ctx.db.execute(delete(FormSubmission).where(FormSubmission.bot_instance_id == other_bot.id))
        ctx.db.commit()
        ctx.db.delete(other_bot)
        ctx.db.commit()


def test_get_submission_denied_without_can_process_submissions(ctx) -> None:
    definition, version = ctx.form()
    student = ctx.make_student()
    sub = ctx.submission(definition=definition, version=version, user=student)
    _, staff_principal = ctx.staff(can_process_submissions=False)

    response = TestClient(ctx.app(staff_principal)).get(f"/submissions/{sub.id}")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "submission_access_denied"


def test_create_submission_happy_path_sets_status_new(ctx) -> None:
    definition, version = ctx.form()
    student = ctx.make_student(complete_profile=True)

    response = TestClient(ctx.app(ctx.student_principal(student))).post(
        "/submissions",
        json={"form_template_id": definition.id, "form_version_id": version.id, "values": {}},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    assert body["user_id"] == student.id


def test_create_submission_rejects_incomplete_profile(ctx) -> None:
    definition, version = ctx.form()
    student = ctx.make_student(complete_profile=False)

    response = TestClient(ctx.app(ctx.student_principal(student))).post(
        "/submissions",
        json={"form_template_id": definition.id, "form_version_id": version.id, "values": {}},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "profile_incomplete"


def test_create_submission_rejects_ban_forms(ctx) -> None:
    definition, version = ctx.form()
    student = ctx.make_student()
    ctx.membership_of(student).ban_forms = True
    ctx.db.commit()

    response = TestClient(ctx.app(ctx.student_principal(student))).post(
        "/submissions",
        json={"form_template_id": definition.id, "form_version_id": version.id, "values": {}},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ban_forms"


def test_create_submission_idempotency_key_replay_returns_same_submission(ctx) -> None:
    definition, version = ctx.form()
    student = ctx.make_student()
    client = TestClient(ctx.app(ctx.student_principal(student)))
    payload = {
        "form_template_id": definition.id,
        "form_version_id": version.id,
        "values": {},
        "idempotency_key": "k-1",
    }

    first = client.post("/submissions", json=payload)
    second = client.post("/submissions", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_patch_status_allowed_transition_sets_taken_at_and_assignee(ctx) -> None:
    definition, version = ctx.form()
    student = ctx.make_student()
    sub = ctx.submission(definition=definition, version=version, user=student)
    admin, staff_principal = ctx.staff()

    response = TestClient(ctx.app(staff_principal)).patch(
        f"/submissions/{sub.id}/status", json={"status": "in_work"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_work"
    assert body["taken_at"] is not None
    assert body["assignee_admin_id"] == admin.id


def test_patch_status_rejects_disallowed_transition(ctx) -> None:
    definition, version = ctx.form()
    student = ctx.make_student()
    sub = ctx.submission(definition=definition, version=version, user=student)
    _, staff_principal = ctx.staff()

    response = TestClient(ctx.app(staff_principal)).patch(
        f"/submissions/{sub.id}/status", json={"status": "done"}
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "bad_status_transition"
