"""Список разговоров для сотрудников (§8.3 ТЗ).

Тикет — это сообщение от студента «без ответа». Здесь мы собираем
список последних разговоров с признаком «есть неотвеченное».
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from ....api.deps import CurrentPrincipal, require_staff
from ....core.errors import not_found
from ....db.session import get_db
from ....models.enums import MessageDirectionEnum
from ...admins.infrastructure.models import Admin
from ...bot_instances.domain.entities import BotInstance
from ...knowledge_base.domain.entities import STAFF_REQUESTED_CLASSIFICATIONS
from ...profiles.infrastructure.models import BotMembershipRecord, User
from ...tenancy.presentation.dependencies import require_tenant_access
from ..infrastructure.models import Message, StaffFavorite
from .schemas import ConversationItem, StaffFavoriteIn, TicketsOverview

router = APIRouter()


@router.get("/overview", response_model=TicketsOverview)
def tickets_overview(
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
) -> TicketsOverview:
    """Сводная статистика для бейджа в навбаре."""
    # «Открытый тикет» = существуют входящие сообщения, после которых нет исходящего
    last_inbound = (
        select(Message.user_id, func.max(Message.created_at).label("last_in"))
        .where(
            Message.bot_instance_id == bot.id,
            Message.direction == MessageDirectionEnum.in_,
        )
        .group_by(Message.user_id)
        .subquery()
    )
    last_outbound = (
        select(Message.user_id, func.max(Message.created_at).label("last_out"))
        .where(
            Message.bot_instance_id == bot.id,
            Message.direction == MessageDirectionEnum.out,
        )
        .group_by(Message.user_id)
        .subquery()
    )

    open_q = (
        select(func.count())
        .select_from(last_inbound)
        .outerjoin(last_outbound, last_inbound.c.user_id == last_outbound.c.user_id)
        .where((last_outbound.c.last_out.is_(None)) | (last_outbound.c.last_out < last_inbound.c.last_in))
    )
    open_count = db.execute(open_q).scalar_one()
    return TicketsOverview(open_count=open_count, unread_count=open_count)


@router.get("/conversations", response_model=list[ConversationItem])
def list_conversations(
    support_id: int | None = Query(default=None),
    query: str | None = Query(default=None, max_length=200),
    user_id: int | None = Query(default=None, ge=1),
    only_open: bool = Query(default=False),
    only_free: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    staff: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[ConversationItem]:
    """Список последних разговоров. Сортировка — по дате последнего сообщения."""

    # support_id из query — в приоритете; иначе используем текущего сотрудника
    effective_support_id = support_id if support_id is not None else staff.admin_id

    last_msg_subq = (
        select(
            Message.user_id,
            func.max(Message.created_at).label("last_at"),
        )
        .where(Message.bot_instance_id == bot.id)
        .group_by(Message.user_id)
        .subquery()
    )

    last_in_subq = (
        select(
            Message.user_id,
            func.max(Message.created_at).label("last_in"),
        )
        .where(
            Message.bot_instance_id == bot.id,
            Message.direction == MessageDirectionEnum.in_,
        )
        .group_by(Message.user_id)
        .subquery()
    )
    last_out_subq = (
        select(
            Message.user_id,
            func.max(Message.created_at).label("last_out"),
        )
        .where(
            Message.bot_instance_id == bot.id,
            Message.direction == MessageDirectionEnum.out,
        )
        .group_by(Message.user_id)
        .subquery()
    )

    # Отдельный alias для "моих" избранных — независимо от effective_support_id,
    # чтобы my_favorite всегда отражал именно текущего сотрудника
    MyFavorite = aliased(StaffFavorite)

    q = (
        select(
            User,
            last_msg_subq.c.last_at,
            last_in_subq.c.last_in,
            last_out_subq.c.last_out,
            StaffFavorite.id,
            MyFavorite.id,
        )
        .join(last_msg_subq, last_msg_subq.c.user_id == User.id)
        .outerjoin(last_in_subq, last_in_subq.c.user_id == User.id)
        .outerjoin(last_out_subq, last_out_subq.c.user_id == User.id)
        .outerjoin(
            StaffFavorite,
            and_(
                StaffFavorite.user_id == User.id,
                StaffFavorite.support_id == effective_support_id,
                StaffFavorite.bot_instance_id == bot.id,
            ),
        )
        .outerjoin(
            MyFavorite,
            and_(
                MyFavorite.user_id == User.id,
                MyFavorite.support_id == staff.admin_id,
                MyFavorite.bot_instance_id == bot.id,
            ),
        )
    )

    if only_free:
        q = q.where(
            or_(
                StaffFavorite.user_id.is_(None),
                MyFavorite.user_id.isnot(None),
            )
        )

    if user_id is not None:
        q = q.where(User.id == user_id)
    if query and query.strip():
        search = f"%{query.strip()}%"
        full_name = func.concat_ws(
            " ",
            func.coalesce(User.last_name, ""),
            func.coalesce(User.first_name, ""),
            func.coalesce(User.patronymic, ""),
        )
        q = q.where(
            or_(
                full_name.ilike(search),
                User.first_name.ilike(search),
                User.last_name.ilike(search),
                User.patronymic.ilike(search),
                User.user_id.ilike(search),
            )
        )

    q = q.order_by(desc(last_msg_subq.c.last_at)).limit(limit)

    rows = list(db.execute(q).all())
    user_ids = [u.id for u, *_ in rows]
    last_msgs: dict[int, Message] = {}
    if user_ids:
        for user_id in user_ids:
            m = db.execute(
                select(Message)
                .where(Message.bot_instance_id == bot.id, Message.user_id == user_id)
                .order_by(desc(Message.created_at))
                .limit(1)
            ).scalar_one_or_none()
            if m is not None:
                last_msgs[user_id] = m

    out: list[ConversationItem] = []
    for u, last_at, last_in, last_out, is_favorite, my_favorite in rows:
        has_open = last_in is not None and (last_out is None or last_out < last_in)
        if only_open and not has_open:
            continue
        last = last_msgs.get(u.id)
        # Открытый тикет, последнее сообщение в котором — явный запрос человека
        # (кнопка «Позвать сотрудника» или совпадение по ключевым словам в тексте,
        # см. ai_classification "kb_staff_requested"/"kb_staff_requested_text" в
        # messages_router.py) — бейдж во frontend-admin показывает такие обращения отдельно.
        staff_requested = has_open and bool(
            last is not None and last.ai_classification in STAFF_REQUESTED_CLASSIFICATIONS
        )

        out.append(
            ConversationItem(
                user_id=u.id,
                max_user_id=u.user_id,
                first_name=u.first_name,
                last_name=u.last_name,
                username=u.username,
                photo_url=u.photo_url,
                system=u.system,
                last_message_text=(last.text if last else None),
                last_message_at=last_at,
                unread_count=1 if has_open else 0,
                has_open_ticket=has_open,
                is_favorite=bool(is_favorite),
                my_favorite=bool(my_favorite),
                staff_requested=staff_requested,
            )
        )
    return out


@router.post("/favorites")
def set_favorite(
    payload: StaffFavoriteIn,
    db: Session = Depends(get_db),
    staff: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
):
    membership = db.execute(
        select(BotMembershipRecord.id).where(
            BotMembershipRecord.bot_instance_id == bot.id,
            BotMembershipRecord.user_id == payload.user_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise not_found("Пользователь не найден в выбранном боте")
    if payload.is_favorite:
        stmt = (
            insert(StaffFavorite)
            .values(
                bot_instance_id=bot.id,
                user_id=payload.user_id,
                support_id=staff.admin_id,
            )
            .on_conflict_do_nothing(
                index_elements=["bot_instance_id", "user_id", "support_id"]
            )
        )
    else:
        stmt = delete(StaffFavorite).where(
            StaffFavorite.user_id == payload.user_id,
            StaffFavorite.support_id == staff.admin_id,
            StaffFavorite.bot_instance_id == bot.id,
        )
    db.execute(stmt)
    db.commit()

    is_favorite = db.query(
        db.query(StaffFavorite)
        .filter(
            StaffFavorite.bot_instance_id == bot.id,
            StaffFavorite.user_id == payload.user_id,
        )
        .exists()
    ).scalar()

    return {
        "user_id": payload.user_id,
        "is_favorite": is_favorite,
        "my_favorite": payload.is_favorite,
    }


@router.get("/admins")
def get_admins_ticket(
    user_id: int,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
):
    q = (
        select(Admin.full_name)
        .join(StaffFavorite.support)
        .where(
            StaffFavorite.bot_instance_id == bot.id,
            StaffFavorite.user_id == user_id,
        )
    )
    return db.execute(q).scalars().all()
