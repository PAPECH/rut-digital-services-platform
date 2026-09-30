from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ....api.deps import CurrentPrincipal, require_admin, require_staff
from ....core.errors import forbidden, not_found
from ....db.session import get_db
from ....models.enums import SystemEnum
from ....services.rate_limit import rate_limit
from ...admins.infrastructure.models import Admin
from ...bot_instances.domain.entities import BotInstance
from ...campaign_links.infrastructure.models import CampaignLinkRecord
from ...consent.application.use_cases import GetConsentStatus
from ...consent.infrastructure.repositories import SqlAlchemyConsentRepository
from ...forms.infrastructure.models import FormSubmission
from ...forms.presentation.submissions_schemas import SubmissionOut
from ...support_chat.infrastructure.models import Message
from ...support_chat.presentation.schemas import MessageOut
from ...tenancy.presentation.dependencies import require_tenant_access
from ..infrastructure.models import BotMembershipRecord, User
from .admin_schemas import BanPatchIn, CampaignSourceOut, UserSummary

router = APIRouter()

_ban_rl = rate_limit("user_ban", limit=30, window_seconds=60)

# История переписки в карточке пользователя — окно последних N сообщений.
_USER_MESSAGES_LIMIT = 200


def _summary(
    db: Session,
    user: User,
    membership: BotMembershipRecord,
    campaign_link: CampaignLinkRecord | None = None,
) -> UserSummary:
    data = UserSummary.model_validate(user, from_attributes=True).model_dump()
    for key in (
        "ban_chat",
        "ban_chat_reason",
        "ban_forms",
        "ban_forms_reason",
        "ban_app",
        "ban_app_reason",
    ):
        data[key] = getattr(membership, key)
    consent_state = GetConsentStatus(SqlAlchemyConsentRepository(db)).execute(
        user.user_id, user.system.value
    )
    data["consent_given_at"] = consent_state.given_at if consent_state else None
    data["consent_revoked_at"] = consent_state.revoked_at if consent_state else None
    data["consent_deletion_due_at"] = consent_state.deletion_due_at if consent_state else None
    data["campaign_source"] = (
        CampaignSourceOut(
            code=campaign_link.code,
            campaign=campaign_link.campaign,
            source=campaign_link.source,
            placement=campaign_link.placement,
            target=campaign_link.target,
        )
        if campaign_link is not None
        else None
    )
    return UserSummary(**data)


@router.get("", response_model=list[UserSummary])
def list_users(
    query: str | None = Query(default=None, description="Поиск по имени/username"),
    system: SystemEnum | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[UserSummary]:
    q = (
        select(User, BotMembershipRecord)
        .join(BotMembershipRecord, BotMembershipRecord.user_id == User.id)
        .where(BotMembershipRecord.bot_instance_id == bot.id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if system:
        q = q.where(User.system == system)
    if query:
        like = f"%{query}%"
        q = q.where(
            or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.patronymic.ilike(like),
                User.username.ilike(like),
                User.phone.ilike(like),
                User.email.ilike(like),
                User.user_id.ilike(like),
                User.study_group.ilike(like),
            )
        )
    rows = db.execute(q).all()
    campaign_link_ids = {
        membership.source_campaign_link_id
        for _, membership in rows
        if membership.source_campaign_link_id is not None
    }
    campaign_links = (
        {
            link.id: link
            for link in db.execute(
                select(CampaignLinkRecord).where(CampaignLinkRecord.id.in_(campaign_link_ids))
            ).scalars()
        }
        if campaign_link_ids
        else {}
    )
    return [
        _summary(db, user, membership, campaign_links.get(membership.source_campaign_link_id))
        for user, membership in rows
    ]


@router.get("/{user_pk}")
def get_user(
    user_pk: int,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
) -> dict:
    """Карточка пользователя: профиль + история чата + история заявок (§8.5)."""
    user = db.get(User, user_pk)
    if user is None:
        raise not_found("Пользователь не найден")
    membership = db.execute(
        select(BotMembershipRecord).where(
            BotMembershipRecord.bot_instance_id == bot.id,
            BotMembershipRecord.user_id == user.id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise not_found("Пользователь не найден")

    campaign_link = (
        db.get(CampaignLinkRecord, membership.source_campaign_link_id)
        if membership.source_campaign_link_id is not None
        else None
    )

    # joinedload по relationship Message.replied_by_admin — чтобы не было N+1
    # при сериализации MessageOut.replied_by_admin_name.
    messages = list(
        db.execute(
            select(Message)
            .options(selectinload(Message.replied_by_admin))
            .where(Message.bot_instance_id == bot.id, Message.user_id == user.id)
            .order_by(Message.created_at.desc())
            .limit(_USER_MESSAGES_LIMIT)
        ).scalars()
    )
    messages.reverse()  # отдаём по возрастанию created_at

    submissions = list(
        db.execute(
            select(FormSubmission)
            .where(
                FormSubmission.bot_instance_id == bot.id,
                FormSubmission.user_id == user.id,
            )
            .order_by(FormSubmission.created_at.desc())
        ).scalars()
    )

    return {
        "user": _summary(db, user, membership, campaign_link).model_dump(mode="json"),
        "profile_fields": [
            {
                "key": str(field.get("key") or ""),
                "label": str(field.get("label") or field.get("key") or "Поле"),
                "value": getattr(user, str(field.get("key") or ""), None)
                if hasattr(user, str(field.get("key") or ""))
                else (membership.local_data or {}).get(str(field.get("key") or "")),
            }
            for field in bot.profile_schema
        ],
        "messages": [
            MessageOut.model_validate(m, from_attributes=True).model_dump(mode="json") for m in messages
        ],
        "submissions": [
            SubmissionOut.model_validate(s, from_attributes=True).model_dump(mode="json") for s in submissions
        ],
    }


def _user_belongs_to_admin(db: Session, user: User, admin_id: int | None) -> bool:
    """True, если этот user — «теневой» аккаунт текущего админа (тот же max_user_id).

    Пользователи (User) и сотрудники (Admin) — разные таблицы. Но если админ
    зашёл когда-то и как студент, у него есть и тот, и другой профиль с одинаковым
    max_user_id. Защитимся от случайного локаута администратора через эту запись.
    """
    if admin_id is None:
        return False
    admin = db.get(Admin, admin_id)
    if admin is None:
        return False
    return user.user_id == admin.max_user_id


@router.patch(
    "/{user_pk}/ban",
    response_model=UserSummary,
    dependencies=[Depends(_ban_rl)],
)
def patch_ban(
    user_pk: int,
    payload: BanPatchIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
) -> UserSummary:
    """Управление блокировками пользователя (только админ).

    Можно ставить/снимать любую комбинацию из ban_chat / ban_forms / ban_app
    и опционально задавать причину для каждой. Поля, не переданные в теле,
    остаются без изменений.

    Защиты:
      - админ не может банить «свой» user-аккаунт (тот же max_user_id);
      - в Pydantic-схеме BanPatchIn нет посторонних полей (защита от set чужих полей).
    """
    user = db.get(User, user_pk)
    if user is None:
        raise not_found("Пользователь не найден")
    membership = db.execute(
        select(BotMembershipRecord).where(
            BotMembershipRecord.bot_instance_id == bot.id,
            BotMembershipRecord.user_id == user.id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise not_found("Пользователь не найден")

    if _user_belongs_to_admin(db, user, p.admin_id):
        raise forbidden(
            "Нельзя выставлять блокировку на собственный аккаунт",
            code="self_ban_forbidden",
        )

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(membership, k, v)

    db.commit()
    db.refresh(membership)
    campaign_link = (
        db.get(CampaignLinkRecord, membership.source_campaign_link_id)
        if membership.source_campaign_link_id is not None
        else None
    )
    return _summary(db, user, membership, campaign_link)
