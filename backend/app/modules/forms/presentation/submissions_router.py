from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import Float, cast, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ....api.deps import (
    CurrentPrincipal,
    get_current_principal,
    require_staff,
    require_student,
)
from ....core.errors import bad_request, conflict, forbidden, not_found
from ....db.session import get_db
from ....models.attachment import Attachment
from ....models.enums import SubmissionStatusEnum
from ....services.files import open_file
from ....services.log_action import ActionType, log_action
from ....services.push import enqueue_push
from ....services.rate_limit import rate_limit
from ....services.translation import translate_values_to_en
from ....services.ws_hub import hub, staff_room
from ...bot_instances.domain.entities import BotInstance
from ...bot_instances.infrastructure.models import AdminBotAccessRecord
from ...maintenance.presentation.dependencies import (
    enforce_user_access_available,
    enforce_user_write_available,
)
from ...profiles.domain.requirements import find_missing_required_fields
from ...profiles.domain.snapshots import build_submission_profile_snapshot
from ...profiles.infrastructure.gateways import SqlAlchemyProfileGateway
from ...profiles.infrastructure.models import BotMembershipRecord, User
from ...tenancy.presentation.dependencies import require_tenant_access
from ..application.submission_attachments import ResolveSubmissionAttachmentFields
from ..application.use_cases import (
    FormAttachmentRejected,
    FormNotAvailable,
    FormNotFound,
    FormVersionMismatch,
    GetPublishedForm,
    ValidateSubmission,
)
from ..domain.fields import FormValueValidationError
from ..infrastructure.models import (
    FormDefinitionRecord,
    FormSubmission,
    SubmissionAppointmentSlot,
    SubmissionStatusHistory,
)
from ..infrastructure.repositories import (
    SqlAlchemyFormAttachmentGateway,
    SqlAlchemyFormRepository,
)
from .submissions_schemas import (
    AppointmentBookIn,
    AppointmentOut,
    AppointmentSlotOut,
    StatusHistoryOut,
    StatusPatchIn,
    SubmissionAttachmentOut,
    SubmissionDetailed,
    SubmissionIn,
    SubmissionOut,
    SubmitterOut,
)

_MSK = ZoneInfo("Europe/Moscow")
_APPOINTMENT_LOCATION = "Главный корпус РУТ (МИИТ), кабинет 1201"
_APPOINTMENT_SLOT = timedelta(minutes=15)


def _appointment_out(sub: FormSubmission) -> AppointmentOut | None:
    slots = sorted(sub.appointment_slots or [], key=lambda item: item.starts_at)
    if not slots:
        return None
    starts_at = slots[0].starts_at
    ends_at = slots[-1].starts_at + _APPOINTMENT_SLOT
    return AppointmentOut(
        starts_at=starts_at,
        ends_at=ends_at,
        duration_minutes=len(slots) * 15,
        location=_APPOINTMENT_LOCATION,
    )


def _build_detailed(db: Session, sub: FormSubmission, *, include_history: bool = True) -> SubmissionDetailed:
    u = db.get(User, sub.user_id)
    base = SubmissionOut.model_validate(sub, from_attributes=True).model_dump()
    return SubmissionDetailed(
        **base,
        history=(
            [StatusHistoryOut.model_validate(h, from_attributes=True) for h in sub.history]
            if include_history and sub.history is not None
            else []
        ),
        submitter=SubmitterOut(
            id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            patronymic=u.patronymic,
            username=u.username,
            photo_url=u.photo_url,
            user_id=u.user_id,
            system=u.system.value if u.system else None,
            birth_date=u.birth_date,
            study_group=u.study_group,
            phone=u.phone,
            phone_verified=u.phone_verified,
            email=u.email,
        )
        if u
        else None,
        form_name=sub.form_snapshot.get("name"),
        appointment=_appointment_out(sub),
    )


_submit_rl = rate_limit("submission_create", limit=10, window_seconds=60)
_status_rl = rate_limit("submission_status", limit=60, window_seconds=60)

router = APIRouter(dependencies=[Depends(enforce_user_access_available)])


def _ensure_can_process_submissions(
    db: Session,
    principal: CurrentPrincipal,
    bot_instance_id: int,
) -> None:
    if principal.role == "student" or principal.is_platform_admin:
        return
    access = db.execute(
        select(AdminBotAccessRecord.id).where(
            AdminBotAccessRecord.admin_id == principal.admin_id,
            AdminBotAccessRecord.bot_instance_id == bot_instance_id,
            AdminBotAccessRecord.can_process_submissions.is_(True),
        )
    ).scalar_one_or_none()
    if access is None:
        raise forbidden(
            "Нет права на обработку заявок",
            code="submission_access_denied",
        )


def _attachment_submission(
    db: Session,
    submission_id: int,
    bot: BotInstance,
    principal: CurrentPrincipal,
) -> FormSubmission:
    submission = db.execute(
        select(FormSubmission).where(
            FormSubmission.id == submission_id,
            FormSubmission.bot_instance_id == bot.id,
        )
    ).scalar_one_or_none()
    if submission is None:
        raise not_found("Заявка не найдена")
    if principal.role == "student":
        if principal.user_id != submission.user_id:
            raise not_found("Заявка не найдена")
        return submission
    _ensure_can_process_submissions(db, principal, bot.id)
    return submission


def _attachment_fields(
    db: Session,
    submission: FormSubmission,
    bot_instance_id: int,
) -> dict[int, str]:
    return ResolveSubmissionAttachmentFields(SqlAlchemyFormRepository(db)).execute(
        bot_instance_id=bot_instance_id,
        form_id=submission.form_template_id,
        version_id=submission.form_version_id,
        form_snapshot=submission.form_snapshot,
        values=submission.values,
    )


@router.get("/{submission_id}/attachments", response_model=list[SubmissionAttachmentOut])
def list_submission_attachments(
    submission_id: int,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(get_current_principal),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[SubmissionAttachmentOut]:
    submission = _attachment_submission(db, submission_id, bot, principal)
    attachment_fields = _attachment_fields(db, submission, bot.id)
    if not attachment_fields:
        return []
    attachments = db.execute(
        select(Attachment).where(
            Attachment.bot_instance_id == bot.id,
            Attachment.uploaded_by_user_id == submission.user_id,
            Attachment.id.in_(attachment_fields),
        )
    ).scalars()
    return [
        SubmissionAttachmentOut(
            id=attachment.id,
            field_key=attachment_fields[attachment.id],
            name=attachment.original_name,
            mime=attachment.mime,
            size_bytes=attachment.size_bytes,
            preview_url=f"/submissions/{submission.id}/attachments/{attachment.id}",
            download_url=f"/submissions/{submission.id}/attachments/{attachment.id}?download=true",
        )
        for attachment in attachments
    ]


@router.get("/{submission_id}/attachments/{attachment_id}")
def read_submission_attachment(
    submission_id: int,
    attachment_id: int,
    download: bool = Query(default=False),
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(get_current_principal),
    bot: BotInstance = Depends(require_tenant_access),
) -> FileResponse:
    submission = _attachment_submission(db, submission_id, bot, principal)
    attachment_fields = _attachment_fields(db, submission, bot.id)
    if attachment_id not in attachment_fields:
        raise not_found("Файл не найден")
    attachment = db.execute(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.bot_instance_id == bot.id,
            Attachment.uploaded_by_user_id == submission.user_id,
        )
    ).scalar_one_or_none()
    if attachment is None:
        raise not_found("Файл не найден")
    return FileResponse(
        path=str(open_file(attachment.storage_path)),
        media_type=attachment.mime,
        filename=attachment.original_name,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("", response_model=list[SubmissionDetailed])
def list_submissions(  # noqa: PLR0912
    request: Request,
    form_id: int | None = Query(default=None),
    status: SubmissionStatusEnum | None = Query(default=None),
    limit: int = Query(default=100, ge=-1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(get_current_principal),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[SubmissionDetailed]:
    _ensure_can_process_submissions(db, p, bot.id)
    q = (
        select(FormSubmission)
        .options(
            selectinload(FormSubmission.history),
            selectinload(FormSubmission.appointment_slots),
        )
        .order_by(FormSubmission.created_at.desc())
        .where(FormSubmission.bot_instance_id == bot.id)
    )
    if p.role == "student":
        q = q.where(FormSubmission.user_id == p.user_id)
    else:
        if form_id:
            q = q.where(FormSubmission.form_template_id == form_id)
        if status:
            q = q.where(FormSubmission.status == status)

        # Filters are built from the current published schema. Historical
        # submissions remain readable through their immutable snapshots.
        if form_id:
            published = SqlAlchemyFormRepository(db).get_published(bot.id, form_id)
            fields = published.version.fields if published else []
            for f in fields:
                if not f.get("active", True):
                    continue
                field_key = str(f["key"])
                key = f"f_{field_key}"
                if f["type"] in {"short_text", "long_text", "email", "phone", "select", "radio"}:
                    v = request.query_params.get(key)
                    if v:
                        q = q.where(FormSubmission.values[field_key].astext.ilike(f"%{v}%"))
                elif f["type"] == "number":
                    v_from = request.query_params.get(f"{key}__from")
                    v_to = request.query_params.get(f"{key}__to")
                    try:
                        if v_from:
                            q = q.where(cast(FormSubmission.values[field_key].astext, Float) >= float(v_from))
                        if v_to:
                            q = q.where(cast(FormSubmission.values[field_key].astext, Float) <= float(v_to))
                    except (TypeError, ValueError):
                        pass
                elif f["type"] == "date":
                    v_from = request.query_params.get(f"{key}__from")
                    v_to = request.query_params.get(f"{key}__to")
                    if v_from:
                        q = q.where(FormSubmission.values[field_key].astext >= v_from)
                    if v_to:
                        q = q.where(FormSubmission.values[field_key].astext <= v_to)
                elif f["type"] == "checkbox":
                    v = request.query_params.get(key)
                    if v in ("true", "false"):
                        q = q.where(FormSubmission.values[field_key].astext == v)
    if limit > 0:
        q = q.limit(limit).offset(offset)
    rows = list(db.execute(q).scalars())

    user_ids = {r.user_id for r in rows}
    users = {u.id: u for u in db.execute(select(User).where(User.id.in_(user_ids))).scalars()}

    out: list[SubmissionDetailed] = []
    for r in rows:
        u = users.get(r.user_id)
        base = SubmissionOut.model_validate(r, from_attributes=True).model_dump()
        out.append(
            SubmissionDetailed(
                **base,
                history=[],
                submitter=SubmitterOut(
                    id=u.id,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    patronymic=u.patronymic,
                    username=u.username,
                    photo_url=u.photo_url,
                    user_id=u.user_id,
                    system=u.system.value if u.system else None,
                    birth_date=u.birth_date,
                    study_group=u.study_group,
                    phone=u.phone,
                    phone_verified=u.phone_verified,
                    email=u.email,
                )
                if u
                else None,
                form_name=r.form_snapshot.get("name"),
                appointment=_appointment_out(r),
            )
        )
    return out


@router.get("/appointments/slots", response_model=list[AppointmentSlotOut])
def list_appointment_slots(
    date_from: date = Query(),
    date_to: date = Query(),
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[AppointmentSlotOut]:
    _ensure_can_process_submissions(db, p, bot.id)
    if date_to < date_from or (date_to - date_from).days > 120:
        raise bad_request("Некорректный диапазон дат")
    starts_at = datetime.combine(date_from, time.min, tzinfo=_MSK).astimezone(UTC)
    ends_at = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=_MSK).astimezone(UTC)
    rows = db.execute(
        select(SubmissionAppointmentSlot)
        .where(
            SubmissionAppointmentSlot.bot_instance_id == bot.id,
            SubmissionAppointmentSlot.starts_at >= starts_at,
            SubmissionAppointmentSlot.starts_at < ends_at,
        )
        .order_by(SubmissionAppointmentSlot.starts_at)
    ).scalars()
    return [
        AppointmentSlotOut(starts_at=row.starts_at, submission_id=row.submission_id)
        for row in rows
    ]


@router.get("/{submission_id}", response_model=SubmissionDetailed)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(get_current_principal),
    bot: BotInstance = Depends(require_tenant_access),
) -> SubmissionDetailed:
    _ensure_can_process_submissions(db, p, bot.id)
    s = db.execute(
        select(FormSubmission)
        .options(
            selectinload(FormSubmission.history),
            selectinload(FormSubmission.appointment_slots),
        )
        .where(
            FormSubmission.id == submission_id,
            FormSubmission.bot_instance_id == bot.id,
        )
    ).scalar_one_or_none()
    if s is None:
        raise not_found("Заявка не найдена")

    if p.role == "student" and s.user_id != p.user_id:
        raise forbidden("Чужая заявка")

    u = db.get(User, s.user_id)
    return SubmissionDetailed(
        **SubmissionOut.model_validate(s, from_attributes=True).model_dump(),
        history=[StatusHistoryOut.model_validate(h, from_attributes=True) for h in s.history],
        submitter=SubmitterOut(
            id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            patronymic=u.patronymic,
            username=u.username,
            photo_url=u.photo_url,
            user_id=u.user_id,
            system=u.system.value if u.system else None,
            birth_date=u.birth_date,
            study_group=u.study_group,
            phone=u.phone,
            phone_verified=u.phone_verified,
            email=u.email,
        )
        if u
        else None,
        form_name=s.form_snapshot.get("name"),
        appointment=_appointment_out(s),
    )


def _validated_appointment_slots(values: list[datetime]) -> list[datetime]:
    normalized: list[datetime] = []
    for value in values:
        if value.tzinfo is None:
            raise bad_request("Время талона должно содержать часовой пояс")
        local = value.astimezone(_MSK)
        minute_of_day = local.hour * 60 + local.minute
        if local.weekday() != 3:
            raise bad_request("Запись возможна только по четвергам")
        if local.second or local.microsecond or local.minute % 15:
            raise bad_request("Время должно соответствовать 15-минутному талону")
        if minute_of_day < 10 * 60 or minute_of_day > 11 * 60 + 45:
            raise bad_request("Приём проводится с 10:00 до 12:00")
        if local <= datetime.now(tz=_MSK):
            raise bad_request("Нельзя назначить встречу в прошлом")
        normalized.append(local.astimezone(UTC))

    normalized = sorted(set(normalized))
    if len(normalized) != len(values):
        raise bad_request("Талоны не должны повторяться")
    if len(normalized) == 2 and normalized[1] - normalized[0] != _APPOINTMENT_SLOT:
        raise bad_request("Для встречи на 30 минут выберите два соседних талона")
    return normalized


@router.put("/{submission_id}/appointment", response_model=SubmissionDetailed)
async def book_submission_appointment(
    submission_id: int,
    payload: AppointmentBookIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
) -> SubmissionDetailed:
    _ensure_can_process_submissions(db, p, bot.id)
    slot_starts = _validated_appointment_slots(payload.slot_starts)
    submission = db.execute(
        select(FormSubmission)
        .options(
            selectinload(FormSubmission.history),
            selectinload(FormSubmission.appointment_slots),
        )
        .where(
            FormSubmission.id == submission_id,
            FormSubmission.bot_instance_id == bot.id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if submission is None:
        raise not_found("Заявка не найдена")
    if submission.status != SubmissionStatusEnum.in_work:
        raise bad_request("Назначить встречу можно только для заявки в работе")
    if submission.appointment_slots:
        raise conflict("Встреча по этой заявке уже назначена")

    occupied = db.execute(
        select(SubmissionAppointmentSlot.starts_at).where(
            SubmissionAppointmentSlot.bot_instance_id == bot.id,
            SubmissionAppointmentSlot.starts_at.in_(slot_starts),
        )
    ).first()
    if occupied is not None:
        raise conflict("Один из выбранных талонов уже занят")

    now = datetime.now(tz=UTC)
    for starts_at in slot_starts:
        db.add(
            SubmissionAppointmentSlot(
                bot_instance_id=bot.id,
                submission_id=submission.id,
                starts_at=starts_at,
                created_by_admin_id=p.admin_id,
                created_at=now,
            )
        )

    starts_local = slot_starts[0].astimezone(_MSK)
    ends_local = (slot_starts[-1] + _APPOINTMENT_SLOT).astimezone(_MSK)
    date_text = starts_local.strftime("%d.%m.%Y")
    time_text = f"{starts_local:%H:%M}–{ends_local:%H:%M}"
    db.add(
        SubmissionStatusHistory(
            submission_id=submission.id,
            from_status=submission.status,
            to_status=SubmissionStatusEnum.done,
            changed_by=p.admin_id,
            changed_at=now,
            comment=f"Встреча назначена на {date_text}, {time_text}",
        )
    )
    submission.status = SubmissionStatusEnum.done
    submission.closed_at = now
    enqueue_push(
        db,
        bot_instance_id=bot.id,
        user_id=submission.user_id,
        kind="submission_appointment",
        payload={
            "submission_id": submission.id,
            "date": date_text,
            "time": time_text,
            "location": _APPOINTMENT_LOCATION,
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise conflict("Один из выбранных талонов уже занят") from exc

    updated = db.execute(
        select(FormSubmission)
        .options(
            selectinload(FormSubmission.history),
            selectinload(FormSubmission.appointment_slots),
        )
        .where(FormSubmission.id == submission.id)
    ).scalar_one()
    detailed = _build_detailed(db, updated)
    await hub.broadcast(
        staff_room(bot.id),
        {"type": "submission_updated", "data": detailed.model_dump(mode="json")},
    )
    await hub.broadcast(
        f"user:bot:{bot.id}:{updated.user_id}",
        {"type": "submission_updated", "data": detailed.model_dump(mode="json")},
    )
    return detailed


def _get_complete_profile(
    db: Session,
    user_id: int,
    profile_schema: list[dict],
    local_data: dict,
):
    profile = SqlAlchemyProfileGateway(db).get_shared_profile(user_id)
    if profile is None:
        raise not_found("Профиль не найден")
    missing = find_missing_required_fields(profile, profile_schema, local_data)
    if missing:
        raise bad_request(
            "Заполните профиль перед подачей формы: " + ", ".join(missing),
            code="profile_incomplete",
        )
    return profile


@router.post(
    "",
    response_model=SubmissionDetailed,
    status_code=201,
    dependencies=[Depends(_submit_rl)],
)
async def create_submission(
    payload: SubmissionIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    _: None = Depends(enforce_user_write_available),
) -> SubmissionDetailed:
    user = db.get(User, p.user_id)

    if user is None:
        raise not_found("Профиль не найден")
    membership = db.execute(
        select(BotMembershipRecord).where(
            BotMembershipRecord.bot_instance_id == bot.id,
            BotMembershipRecord.user_id == user.id,
        )
    ).scalar_one_or_none()
    if membership is None or not membership.is_active:
        raise forbidden("Доступ к боту отключён", code="membership_inactive")
    if membership.ban_app:
        raise forbidden(membership.ban_app_reason or "Доступ к приложению заблокирован", code="ban_app")
    if membership.ban_forms:
        raise forbidden(membership.ban_forms_reason or "Подача форм заблокирована", code="ban_forms")
    profile = _get_complete_profile(db, user.id, bot.profile_schema, membership.local_data)

    if payload.idempotency_key:
        existing = db.execute(
            select(FormSubmission).where(
                FormSubmission.bot_instance_id == bot.id,
                FormSubmission.idempotency_key == payload.idempotency_key,
            )
        ).scalar_one_or_none()
        if existing:
            if existing.user_id != p.user_id:
                raise conflict("Ключ идемпотентности уже использован", code="idempotency_collision")
            return _build_detailed(db, existing)

    try:
        published = GetPublishedForm(SqlAlchemyFormRepository(db)).execute(
            bot.id,
            payload.form_template_id,
            payload.form_version_id,
        )
    except (FormNotFound, FormNotAvailable) as exc:
        raise not_found("Форма не найдена или неактивна") from exc
    except FormVersionMismatch as exc:
        raise conflict(
            "Версия формы не соответствует выбранной форме",
            code="form_version_mismatch",
        ) from exc
    try:
        normalized = ValidateSubmission(SqlAlchemyFormAttachmentGateway(db)).execute(
            bot_instance_id=bot.id,
            user_id=user.id,
            fields=published.version.fields,
            values=payload.values,
        )
    except FormValueValidationError as exc:
        error_code = (
            "unknown_form_field" if str(exc) == "Unknown or inactive form field" else "invalid_form_value"
        )
        raise bad_request(
            str(exc),
            code=error_code,
            field_key=exc.field_key,
        ) from exc
    except FormAttachmentRejected as exc:
        error_code = (
            "cross_tenant_attachment"
            if exc.reason == "Attachment belongs to another bot"
            else "form_attachment_rejected"
        )
        raise bad_request(
            exc.reason,
            code=error_code,
            attachment_ids=sorted(exc.attachment_ids),
        ) from exc

    values_en = translate_values_to_en(normalized)
    field_labels = {
        str(field["key"]): field["label"]
        for field in published.version.fields
        if str(field["key"]) in normalized
    }
    form_snapshot = {
        "form_id": published.definition.id,
        "form_version_id": published.version.id,
        "version": published.version.version,
        "name": published.version.name,
        "description": published.version.description,
        "reply_on_accept": published.version.reply_on_accept,
        "fields": published.version.fields,
    }

    sub = FormSubmission(
        bot_instance_id=bot.id,
        form_template_id=published.definition.id,
        form_version_id=published.version.id,
        user_id=p.user_id,
        values=normalized,
        values_en=values_en,
        field_labels=field_labels,
        form_snapshot=form_snapshot,
        profile_snapshot=build_submission_profile_snapshot(profile, membership.local_data),
        status=SubmissionStatusEnum.new,
        idempotency_key=payload.idempotency_key,
    )
    db.add(sub)
    db.flush()

    log_action(
        session=db,
        bot_instance_id=bot.id,
        user_id=p.user_id,
        action_type=ActionType.SUBMIT_FORM,
        form_template_id=published.definition.id,
        form_version_id=published.version.id,
    )

    db.add(
        SubmissionStatusHistory(
            submission_id=sub.id,
            from_status=None,
            to_status=SubmissionStatusEnum.new,
            changed_by=None,
            changed_at=datetime.now(tz=UTC),
            comment="Создание заявки",
        )
    )
    if published.version.reply_on_accept:
        enqueue_push(
        db,
        bot_instance_id=bot.id,
        user_id=p.user_id,
        kind="submission_created",
        payload={
            "submission_id": sub.id,
            "reply_on_accept": f"Форма «{published.version.name}» #{sub.id} отправлена.\n\n{published.version.reply_on_accept or ''}".strip(),
        },
        )
    db.commit()
    db.refresh(sub)

    detailed = _build_detailed(db, sub, include_history=False)

    await hub.broadcast(
        staff_room(bot.id),
        {"type": "new_submission", "data": detailed.model_dump(mode="json")},
    )

    return detailed


_ALLOWED_TRANSITIONS: dict[SubmissionStatusEnum, set[SubmissionStatusEnum]] = {
    SubmissionStatusEnum.new: {SubmissionStatusEnum.in_work, SubmissionStatusEnum.rejected},
    SubmissionStatusEnum.in_work: {SubmissionStatusEnum.done, SubmissionStatusEnum.rejected},
    SubmissionStatusEnum.rejected: set(),
    SubmissionStatusEnum.done: set(),
}


@router.patch(
    "/{submission_id}/status",
    response_model=SubmissionDetailed,
    dependencies=[Depends(_status_rl)],
)
async def patch_status(
    submission_id: int,
    payload: StatusPatchIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
) -> SubmissionDetailed:
    _ensure_can_process_submissions(db, p, bot.id)
    s = db.execute(
        select(FormSubmission).where(
            FormSubmission.id == submission_id,
            FormSubmission.bot_instance_id == bot.id,
        )
    ).scalar_one_or_none()
    if s is None:
        raise not_found("Заявка не найдена")

    definition = db.get(FormDefinitionRecord, s.form_template_id)
    if (
        payload.status == SubmissionStatusEnum.done
        and definition is not None
        and definition.slug == "form-priem"
        and not s.appointment_slots
    ):
        raise bad_request("Сначала назначьте дату и время встречи")

    if payload.status not in _ALLOWED_TRANSITIONS.get(s.status, set()):
        raise bad_request(
            f"Переход {s.status.value} → {payload.status.value} запрещён",
            code="bad_status_transition",
        )

    now = datetime.now(tz=UTC)
    db.add(
        SubmissionStatusHistory(
            submission_id=s.id,
            from_status=s.status,
            to_status=payload.status,
            changed_by=p.admin_id,
            changed_at=now,
            comment=payload.comment,
        )
    )

    s.status = payload.status
    if payload.status == SubmissionStatusEnum.in_work and not s.taken_at:
        s.taken_at = now
        s.assignee_admin_id = p.admin_id
    if payload.status in (SubmissionStatusEnum.done, SubmissionStatusEnum.rejected):
        s.closed_at = now

    enqueue_push(
        db,
        bot_instance_id=bot.id,
        user_id=s.user_id,
        kind="submission_status",
        payload={"submission_id": s.id, "status": s.status.value, "comment": payload.comment},
    )
    db.commit()
    db.refresh(s)

    detailed = _build_detailed(db, s)

    await hub.broadcast(
        staff_room(bot.id),
        {"type": "submission_updated", "data": detailed.model_dump(mode="json")},
    )

    await hub.broadcast(
        f"user:bot:{bot.id}:{s.user_id}",
        {"type": "submission_updated", "data": detailed.model_dump(mode="json")},
    )

    return detailed
