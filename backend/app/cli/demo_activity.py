"""Synthetic users, requests, conversations and analytics events for the demo bots.

All people and values here are fictional. Timestamps are relative to the moment of seeding so the
default dashboard period shows them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import (
    MessageDirectionEnum,
    SubmissionStatusEnum,
    SystemEnum,
)
from ..models.logger import UserAction
from ..modules.admins.infrastructure.models import Admin
from ..modules.analytics.domain.events import AnalyticsEventName
from ..modules.bot_instances.application.staff_access_commands import GrantStaffAccessCommand
from ..modules.bot_instances.application.staff_access_use_cases import GrantBotStaffAccess
from ..modules.bot_instances.domain.staff_access import StaffPermissions
from ..modules.bot_instances.infrastructure.models import BotInstanceRecord
from ..modules.bot_instances.infrastructure.staff_access_repository import (
    SqlAlchemyStaffAccessRepository,
)
from ..modules.forms.application.use_cases import ValidateSubmission
from ..modules.forms.infrastructure.models import (
    FormDefinitionRecord,
    FormSubmission,
    FormVersionRecord,
    SubmissionStatusHistory,
)
from ..modules.forms.infrastructure.repositories import SqlAlchemyFormAttachmentGateway
from ..modules.knowledge_base.domain.entities import MessageAiClassificationEnum
from ..modules.profiles.domain.snapshots import build_submission_profile_snapshot
from ..modules.profiles.infrastructure.gateways import SqlAlchemyProfileGateway
from ..modules.profiles.infrastructure.models import BotMembershipRecord, User
from ..modules.support_chat.infrastructure.models import Message
from ..services.translation import translate_values_to_en

STUDENTS = (
    ("Анна", "Тестова", "Демо-кафедра", "Методист"),
    ("Илья", "Примеров", "Демо-институт", "Старший преподаватель"),
    ("Мария", "Образцова", "Демо-деканат", "Специалист"),
    ("Олег", "Демонстров", "Демо-лаборатория", "Инженер"),
    ("Софья", "Пробная", "Демо-кафедра", "Ассистент"),
    ("Павел", "Условный", "Демо-отдел", "Аналитик"),
)


@dataclass(frozen=True, slots=True)
class _Request:
    student: int
    days_ago: float
    in_work_after: timedelta | None = None
    done_after: timedelta | None = None
    rejected_after: timedelta | None = None


MAIN_REQUESTS = (
    _Request(0, 12, timedelta(hours=2), timedelta(days=1)),
    _Request(1, 9, timedelta(minutes=30), timedelta(hours=5)),
    _Request(2, 6, timedelta(hours=1), timedelta(days=2)),
    _Request(3, 4, rejected_after=timedelta(hours=3)),
    _Request(4, 2, timedelta(hours=4)),
    _Request(5, 0.2),
)
SECOND_REQUESTS = (
    _Request(0, 8, timedelta(hours=3), timedelta(hours=20)),
    _Request(2, 3, timedelta(hours=1)),
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _ensure_staff(db: Session, bot_id: int) -> Admin:
    max_user_id = os.getenv("DEMO_STAFF_MAX_ID", "demo-staff")
    GrantBotStaffAccess(SqlAlchemyStaffAccessRepository(db)).execute(
        GrantStaffAccessCommand(
            bot_instance_id=bot_id,
            max_user_id=max_user_id,
            full_name=os.getenv("DEMO_STAFF_FULL_NAME", "Демо Сотрудник"),
            role="employee",
            permissions=StaffPermissions(can_process_submissions=True),
        )
    )
    return db.execute(select(Admin).where(Admin.max_user_id == max_user_id)).scalar_one()


def _ensure_students(db: Session) -> list[User]:
    users: list[User] = []
    for index, (first, last, unit, title) in enumerate(STUDENTS, start=1):
        external_id = f"demo-student-{index}"
        user = db.execute(
            select(User).where(User.user_id == external_id, User.system == SystemEnum.max)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                user_id=external_id,
                system=SystemEnum.max,
                first_name=first,
                last_name=last,
                language_code="ru",
                phone=f"+7900000000{index}",
                email=f"student{index}@example.com",
                birth_date=date(2000 + index, 1, 1),
                job_title=title,
                structural_unit=unit,
            )
            db.add(user)
            db.flush()
        users.append(user)
    return users


def _join(db: Session, bot_id: int, user: User, at: datetime) -> BotMembershipRecord:
    membership = BotMembershipRecord(bot_instance_id=bot_id, user_id=user.id, created_at=at)
    db.add(membership)
    db.flush()
    return membership


def _event(db: Session, bot_id: int, user: User, name: AnalyticsEventName, at: datetime, **extra: Any) -> None:
    db.add(
        UserAction(
            bot_instance_id=bot_id,
            user_id=user.id,
            action_type=name.value,
            created_at=at,
            **extra,
        )
    )


_BY_TYPE: dict[str, Any] = {
    "email": lambda field, user: user.email,
    "phone": lambda field, user: user.phone,
    "date": lambda field, user: (user.birth_date or date(2000, 1, 1)).isoformat(),
    "number": lambda field, user: max(1, int(field.get("min") or 1)),
    "checkbox": lambda field, user: True,
    "select": lambda field, user: field["options"][0]["value"],
    "single_choice": lambda field, user: field["options"][0]["value"],
    "multiselect": lambda field, user: [field["options"][0]["value"]],
    "long_text": lambda field, user: "Демонстрационная заявка.",
}
_BY_KEY: dict[str, Any] = {
    "full_name": lambda user: f"{user.last_name} {user.first_name}",
    "position": lambda user: user.job_title,
    "job_title": lambda user: user.job_title,
    "unit": lambda user: user.structural_unit,
    "structural_unit": lambda user: user.structural_unit,
}


def _sample_value(field: dict[str, Any], user: User) -> Any:
    by_type = _BY_TYPE.get(str(field.get("type")))
    if by_type is not None:
        return by_type(field, user)
    by_key = _BY_KEY.get(str(field.get("key")))
    return by_key(user) if by_key is not None else "Демо"


def _values(db: Session, bot_id: int, user: User, fields: list[dict[str, Any]]) -> dict[str, Any] | None:
    raw = {
        str(field["key"]): _sample_value(field, user)
        for field in fields
        if field.get("active", True) and field.get("type") != "file"
    }
    if any(field.get("required") and field.get("type") == "file" for field in fields):
        return None
    return ValidateSubmission(SqlAlchemyFormAttachmentGateway(db)).execute(
        bot_instance_id=bot_id, user_id=user.id, fields=fields, values=raw
    )


def _published_form(db: Session, bot_id: int, slug: str | None) -> tuple[FormDefinitionRecord, FormVersionRecord] | None:
    query = select(FormDefinitionRecord).where(
        FormDefinitionRecord.bot_instance_id == bot_id,
        FormDefinitionRecord.published_version_id.isnot(None),
        FormDefinitionRecord.is_active.is_(True),
    )
    if slug:
        query = query.where(FormDefinitionRecord.slug == slug)
    for definition in db.execute(query.order_by(FormDefinitionRecord.order, FormDefinitionRecord.id)).scalars():
        version = db.get(FormVersionRecord, definition.published_version_id)
        if version is not None and not any(
            field.get("required") and field.get("type") == "file" for field in version.fields
        ):
            return definition, version
    return None


def _submit(
    db: Session,
    bot_id: int,
    form: tuple[FormDefinitionRecord, FormVersionRecord],
    user: User,
    request: _Request,
    staff: Admin,
) -> None:
    definition, version = form
    values = _values(db, bot_id, user, version.fields)
    if values is None:
        return
    created = _now() - timedelta(days=request.days_ago)
    _event(db, bot_id, user, AnalyticsEventName.FORM_OPEN, created - timedelta(minutes=4), form_template_id=definition.id)
    _event(db, bot_id, user, AnalyticsEventName.FORM_START, created - timedelta(minutes=3), form_template_id=definition.id)
    _event(db, bot_id, user, AnalyticsEventName.SUBMIT_FORM, created, form_template_id=definition.id)

    status = SubmissionStatusEnum.new
    transitions: list[tuple[SubmissionStatusEnum, datetime]] = []
    if request.in_work_after is not None:
        transitions.append((SubmissionStatusEnum.in_work, created + request.in_work_after))
        if request.done_after is not None:
            transitions.append((SubmissionStatusEnum.done, created + request.in_work_after + request.done_after))
    if request.rejected_after is not None:
        transitions.append((SubmissionStatusEnum.rejected, created + request.rejected_after))
    if transitions:
        status = transitions[-1][0]

    submission = FormSubmission(
        bot_instance_id=bot_id,
        form_template_id=definition.id,
        form_version_id=version.id,
        user_id=user.id,
        values=values,
        values_en=translate_values_to_en(values),
        field_labels={str(f["key"]): f["label"] for f in version.fields if str(f["key"]) in values},
        form_snapshot={
            "form_id": definition.id,
            "form_version_id": version.id,
            "version": version.version,
            "name": version.name,
            "description": version.description,
            "reply_on_accept": version.reply_on_accept,
            "fields": version.fields,
        },
        profile_snapshot=build_submission_profile_snapshot(
            SqlAlchemyProfileGateway(db).get_shared_profile(user.id)
        ),
        status=status,
        created_at=created,
    )
    db.add(submission)
    db.flush()
    db.add(
        SubmissionStatusHistory(
            submission_id=submission.id,
            from_status=None,
            to_status=SubmissionStatusEnum.new,
            changed_at=created,
            comment="Создание заявки",
        )
    )
    previous = SubmissionStatusEnum.new
    for target, at in transitions:
        db.add(
            SubmissionStatusHistory(
                submission_id=submission.id,
                from_status=previous,
                to_status=target,
                changed_by=staff.id,
                changed_at=at,
            )
        )
        previous = target


def _message(
    db: Session,
    bot_id: int,
    user: User,
    direction: MessageDirectionEnum,
    text: str,
    at: datetime,
    **extra: Any,
) -> None:
    db.add(
        Message(
            bot_instance_id=bot_id,
            user_id=user.id,
            system=SystemEnum.max,
            direction=direction,
            text=text,
            created_at=at,
            **extra,
        )
    )


def _conversations(db: Session, bot_id: int, users: list[User], staff: Admin, *, with_ai: bool) -> None:
    now = _now()
    asked = now - timedelta(days=5, hours=3)
    _message(db, bot_id, users[1], MessageDirectionEnum.in_, "Подскажите, где забрать готовую справку?", asked)
    _message(
        db,
        bot_id,
        users[1],
        MessageDirectionEnum.out,
        "Готовые документы выдаются в кабинете отдела кадров с 10:00 до 17:00.",
        asked + timedelta(minutes=25),
        replied_by_admin_id=staff.id,
    )
    _message(
        db,
        bot_id,
        users[2],
        MessageDirectionEnum.in_,
        "Можно ли получить справку в электронном виде?",
        now - timedelta(hours=20),
    )
    if with_ai:
        auto_at = now - timedelta(days=2, hours=1)
        _message(
            db,
            bot_id,
            users[0],
            MessageDirectionEnum.in_,
            "Как получить место в общежитии?",
            auto_at,
            is_ai_answered=True,
            ai_classification=MessageAiClassificationEnum.kb_auto,
        )
        _message(
            db,
            bot_id,
            users[0],
            MessageDirectionEnum.out,
            "Ответ из базы знаний: порядок заселения описан в разделе «Заселение».",
            auto_at + timedelta(seconds=3),
            is_ai_answered=True,
            ai_classification=MessageAiClassificationEnum.kb_auto,
        )


def seed_activity(
    db: Session,
    bots: dict[str, BotInstanceRecord],
    *,
    main_slug: str,
    request_form_slug: str,
) -> None:
    users = _ensure_students(db)
    now = _now()
    main = bots.get(main_slug)
    if main is not None:
        staff = _ensure_staff(db, main.id)
        for offset, user in enumerate(users):
            joined = now - timedelta(days=14 - offset)
            _join(db, main.id, user, joined)
            for day in range(0, 14 - offset, 3):
                _event(db, main.id, user, AnalyticsEventName.APP_OPEN, joined + timedelta(days=day, hours=1))
        form = _published_form(db, main.id, request_form_slug)
        if form is not None:
            for request in MAIN_REQUESTS:
                _submit(db, main.id, form, users[request.student], request, staff)
        _conversations(db, main.id, users, staff, with_ai=False)

    for slug, bot in bots.items():
        if slug == main_slug:
            continue
        staff_member = db.execute(
            select(Admin).where(Admin.max_user_id == os.getenv("DEMO_STAFF_MAX_ID", "demo-staff"))
        ).scalar_one_or_none()
        for offset, user in enumerate(users[:3]):
            joined = now - timedelta(days=10 - offset)
            _join(db, bot.id, user, joined)
            _event(db, bot.id, user, AnalyticsEventName.APP_OPEN, joined + timedelta(hours=2))
        form = _published_form(db, bot.id, None)
        if form is not None and staff_member is not None:
            for request in SECOND_REQUESTS:
                _submit(db, bot.id, form, users[request.student], request, staff_member)
        if staff_member is not None:
            _conversations(db, bot.id, users, staff_member, with_ai=True)
    db.flush()
