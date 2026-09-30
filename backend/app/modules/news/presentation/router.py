from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal, require_student
from ....core.errors import bad_request, not_found
from ....db.session import get_db
from ....models.attachment import Attachment
from ....services.files import make_signed_url
from ....services.log_action import ActionType, log_action
from ...bot_instances.domain.entities import BotInstance
from ...content_blocks.domain.errors import BlockValidationError
from ...maintenance.presentation.dependencies import enforce_user_access_available
from ...tenancy.presentation.dependencies import require_tenant_access
from ..application.use_cases import (
    CreateNewsItem,
    DeleteNewsItem,
    ListNewsItems,
    UpdateNewsItem,
)
from ..domain.body import extract_body_attachment_ids
from ..domain.entities import InvalidNewsItem, NewsItem
from ..infrastructure.repositories import SqlAlchemyNewsRepository
from .dependencies import NewsManagerContext, require_news_manager
from .schemas import AttachmentUrlEntry, NewsItemCreateRequest, NewsItemPatchRequest, NewsItemResponse

router = APIRouter()


def _attachment_urls(
    db: Session, *, bot_instance_id: int, attachment_ids: set[int]
) -> dict[int, AttachmentUrlEntry]:
    if not attachment_ids:
        return {}
    rows = db.execute(
        select(Attachment.id, Attachment.mime).where(
            Attachment.bot_instance_id == bot_instance_id,
            Attachment.id.in_(attachment_ids),
        )
    ).all()
    return {
        attachment_id: AttachmentUrlEntry(url=make_signed_url(attachment_id), mime=mime)
        for attachment_id, mime in rows
    }


def _response(item: NewsItem, db: Session) -> NewsItemResponse:
    assert item.id is not None
    assert item.published_at is not None
    return NewsItemResponse(
        id=item.id,
        bot_instance_id=item.bot_instance_id,
        title=item.title,
        title_en=item.title_en,
        body_blocks=item.body_blocks,
        category=item.category,
        cover_attachment_id=item.cover_attachment_id,
        cover_url=make_signed_url(item.cover_attachment_id) if item.cover_attachment_id else None,
        is_active=item.is_active,
        published_at=item.published_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        attachment_urls=_attachment_urls(
            db,
            bot_instance_id=item.bot_instance_id,
            attachment_ids=extract_body_attachment_ids(item.body_blocks),
        ),
    )


@router.get(
    "",
    response_model=list[NewsItemResponse],
    dependencies=[Depends(enforce_user_access_available)],
)
def list_news(
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(get_current_principal),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[NewsItemResponse]:
    repository = SqlAlchemyNewsRepository(db)
    include_inactive = principal.role != "student"
    items = ListNewsItems(repository).execute(bot.id, include_inactive=include_inactive)
    return [_response(item, db) for item in items]


@router.post("", response_model=NewsItemResponse, status_code=status.HTTP_201_CREATED)
def create_news(
    payload: NewsItemCreateRequest,
    context: NewsManagerContext = Depends(require_news_manager),
    db: Session = Depends(get_db),
) -> NewsItemResponse:
    repository = SqlAlchemyNewsRepository(db)
    try:
        item = CreateNewsItem(repository).execute(
            bot_instance_id=context.bot.id,
            title=payload.title,
            title_en=payload.title_en,
            body_blocks=payload.body_blocks,
            category=payload.category,
            cover_attachment_id=payload.cover_attachment_id,
            is_active=payload.is_active,
            published_at=payload.published_at,
        )
    except BlockValidationError as exc:
        raise bad_request(str(exc), code="invalid_news_body") from exc
    except InvalidNewsItem as exc:
        raise bad_request(str(exc), code="invalid_news_item") from exc
    db.commit()
    return _response(item, db)


@router.patch("/{item_id}", response_model=NewsItemResponse)
def patch_news(
    item_id: int,
    payload: NewsItemPatchRequest,
    context: NewsManagerContext = Depends(require_news_manager),
    db: Session = Depends(get_db),
) -> NewsItemResponse:
    repository = SqlAlchemyNewsRepository(db)
    changes = payload.model_dump(exclude_unset=True)
    try:
        item = UpdateNewsItem(repository).execute(context.bot.id, item_id, changes)
    except BlockValidationError as exc:
        raise bad_request(str(exc), code="invalid_news_body") from exc
    except InvalidNewsItem as exc:
        raise bad_request(str(exc), code="invalid_news_item") from exc
    if item is None:
        raise not_found("Новость не найдена", code="news_not_found")
    db.commit()
    return _response(item, db)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(
    item_id: int,
    context: NewsManagerContext = Depends(require_news_manager),
    db: Session = Depends(get_db),
) -> Response:
    repository = SqlAlchemyNewsRepository(db)
    deleted = DeleteNewsItem(repository).execute(context.bot.id, item_id)
    if not deleted:
        raise not_found("Новость не найдена", code="news_not_found")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/events/open", status_code=status.HTTP_204_NO_CONTENT)
def record_news_open(
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> Response:
    if principal.user_id is not None and bot.id is not None:
        log_action(
            session=db,
            bot_instance_id=bot.id,
            user_id=principal.user_id,
            action_type=ActionType.NEWS_OPEN,
            commit=True,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{item_id}/events/open", status_code=status.HTTP_204_NO_CONTENT)
def record_news_item_open(
    item_id: int,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> Response:
    if principal.user_id is not None and bot.id is not None:
        log_action(
            session=db,
            bot_instance_id=bot.id,
            user_id=principal.user_id,
            action_type=ActionType.NEWS_ITEM_OPEN,
            news_id=item_id,
            commit=True,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
