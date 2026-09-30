from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_student
from ....core.errors import bad_request, conflict, not_found
from ....db.session import get_db
from ....services.bot_runtime_auth import authorize_bot_runtime
from ...audit.infrastructure.models import AuditLog
from ....services.rate_limit import rate_limit
from ...bot_instances.domain.entities import BotInstance
from ...bot_instances.infrastructure.models import BotRuntimeRecord
from ...profiles.infrastructure.gateways import SqlAlchemyProfileGateway
from ...tenancy.presentation.dependencies import resolve_tenant
from ..application.use_cases import (
    CampaignLinkCodeTaken,
    CreateCampaignLink,
    DeleteCampaignLink,
    ListCampaignLinks,
    ListUnmatchedCampaignLinks,
    RecordAnonymousCampaignLinkOpen,
    RecordIdentifiedCampaignLinkOpen,
)
from ..domain.entities import (
    CampaignLink,
    CampaignLinkCodeTooLongForBotTarget,
    CampaignLinkTarget,
    CampaignLinkTouch,
    InvalidCampaignLink,
    UnmatchedCodeSummary,
    build_deep_link,
)
from ..infrastructure.repositories import SqlAlchemyCampaignLinkRepository
from .dependencies import CampaignLinkManagerContext, require_campaign_link_manager
from .schemas import (
    CampaignLinkCreateRequest,
    CampaignLinkResponse,
    UnmatchedCampaignLinkResponse,
)

router = APIRouter()

_open_rl = rate_limit("campaign_link_open", limit=30, window_seconds=60)


def _bot_username(db: Session, bot_instance_id: int) -> str | None:
    runtime = db.get(BotRuntimeRecord, bot_instance_id)
    return runtime.username if runtime else None


def _response(link: CampaignLink, *, unique_open_count: int, bot_username: str | None) -> CampaignLinkResponse:
    assert link.id is not None
    return CampaignLinkResponse(
        id=link.id,
        bot_instance_id=link.bot_instance_id,
        code=link.code,
        campaign=link.campaign,
        source=link.source,
        placement=link.placement,
        target=link.target.value,
        created_at=link.created_at,
        open_count=link.open_count,
        unique_open_count=unique_open_count,
        first_open_count=link.open_count,
        repeat_open_count=link.repeat_open_count,
        last_opened_at=link.last_opened_at,
        bot_username=bot_username,
        deep_link=build_deep_link(bot_username or "", link.code, link.target),
    )


def _unmatched_response(summary: UnmatchedCodeSummary) -> UnmatchedCampaignLinkResponse:
    return UnmatchedCampaignLinkResponse(
        code=summary.code,
        event_source=summary.event_source.value,
        hit_count=summary.hit_count,
        last_seen_at=summary.last_seen_at,
    )


def _add_audit(db: Session, *, admin_id: int | None, bot_instance_id: int, link_id: int, action: str) -> None:
    db.add(
        AuditLog(
            admin_id=admin_id,
            bot_instance_id=bot_instance_id,
            method="CAMPAIGN",
            path=f"/api/campaign-links/{link_id}",
            status_code=200,
            meta={"action": action, "campaign_link_id": link_id},
        )
    )


@router.post("", response_model=CampaignLinkResponse)
def create_campaign_link(
    payload: CampaignLinkCreateRequest,
    context: CampaignLinkManagerContext = Depends(require_campaign_link_manager),
    db: Session = Depends(get_db),
) -> CampaignLinkResponse:
    bot = context.bot
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    repository = SqlAlchemyCampaignLinkRepository(db)
    try:
        target = CampaignLinkTarget(payload.target)
        link = CreateCampaignLink(repository).execute(
            bot_instance_id=bot.id,
            code=payload.code,
            campaign=payload.campaign,
            source=payload.source,
            placement=payload.placement,
            target=target,
            created_by_admin_id=context.principal.admin_id,
        )
    except CampaignLinkCodeTooLongForBotTarget as exc:
        raise bad_request(str(exc), code="code_too_long_for_bot_target") from exc
    except InvalidCampaignLink as exc:
        raise bad_request(str(exc), code="invalid_campaign_link") from exc
    except CampaignLinkCodeTaken as exc:
        raise conflict("Code already used for this bot", code="campaign_link_code_taken") from exc
    _add_audit(db, admin_id=context.principal.admin_id, bot_instance_id=bot.id, link_id=link.id or 0, action="create")
    db.commit()
    return _response(link, unique_open_count=0, bot_username=_bot_username(db, bot.id))


@router.get("", response_model=list[CampaignLinkResponse])
def list_campaign_links(
    context: CampaignLinkManagerContext = Depends(require_campaign_link_manager),
    db: Session = Depends(get_db),
) -> list[CampaignLinkResponse]:
    bot = context.bot
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    repository = SqlAlchemyCampaignLinkRepository(db)
    pairs = ListCampaignLinks(repository).execute(bot.id)
    bot_username = _bot_username(db, bot.id)
    return [
        _response(link, unique_open_count=unique_count, bot_username=bot_username)
        for link, unique_count in pairs
    ]


@router.get("/unmatched", response_model=list[UnmatchedCampaignLinkResponse])
def list_unmatched_campaign_links(
    context: CampaignLinkManagerContext = Depends(require_campaign_link_manager),
    db: Session = Depends(get_db),
) -> list[UnmatchedCampaignLinkResponse]:
    bot = context.bot
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    repository = SqlAlchemyCampaignLinkRepository(db)
    summaries = ListUnmatchedCampaignLinks(repository).execute(bot.id)
    return [_unmatched_response(s) for s in summaries]


@router.delete("/{link_id}", status_code=204)
def delete_campaign_link(
    link_id: int,
    context: CampaignLinkManagerContext = Depends(require_campaign_link_manager),
    db: Session = Depends(get_db),
) -> Response:
    bot = context.bot
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    repository = SqlAlchemyCampaignLinkRepository(db)
    link = DeleteCampaignLink(repository).execute(bot.id, link_id)
    if link is None:
        raise not_found("Campaign link not found", code="campaign_link_not_found")
    _add_audit(db, admin_id=context.principal.admin_id, bot_instance_id=bot.id, link_id=link_id, action="delete")
    db.commit()
    return Response(status_code=204)


@router.post("/{code}/open", status_code=204)
def open_campaign_link(
    code: str,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    _rl: None = Depends(_open_rl),
) -> Response:
    if bot.id is not None and principal.user_id is not None:
        repository = SqlAlchemyCampaignLinkRepository(db)
        RecordIdentifiedCampaignLinkOpen(repository, SqlAlchemyProfileGateway(db)).execute(
            bot.id, code, principal.user_id
        )
        db.commit()
    return Response(status_code=204)


@router.post("/{code}/open/bot", status_code=204)
def open_campaign_link_bot(
    code: str,
    touch: Literal["first", "repeat"] = Query(...),
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    x_bot_token: str | None = Header(default=None, alias="X-Bot-Token"),
    x_bot_runtime_token: str | None = Header(default=None, alias="X-Bot-Runtime-Token"),
) -> Response:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    authorize_bot_runtime(db, bot.id, x_bot_runtime_token, x_bot_token)
    RecordAnonymousCampaignLinkOpen(SqlAlchemyCampaignLinkRepository(db)).execute(
        bot.id, code, CampaignLinkTouch(touch)
    )
    db.commit()
    return Response(status_code=204)
