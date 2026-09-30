from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_platform_admin, require_staff, require_student
from ....core.errors import bad_request
from ....db.session import get_db
from ...bot_instances.domain.entities import BotInstance
from ...tenancy.presentation.dependencies import require_tenant_access
from ..application.dashboard_use_cases import (
    GetBotDashboard,
    GetPlatformDashboard,
    InvalidDashboardPeriod,
    resolve_period,
)
from ..application.use_cases import RecordAnalyticsEvent
from ..domain.events import (
    AnalyticsEvent,
    AnalyticsEventName,
    ContentInteractionKind,
    InvalidAnalyticsEvent,
    SourceSurface,
)
from ..infrastructure.dashboard_repository import SqlAlchemyDashboardRepository
from ..infrastructure.event_repository import SqlAlchemyAnalyticsEventRepository
from .dashboard_schemas import BotDashboardResponse, PlatformDashboardResponse
from .event_schemas import AnalyticsEventRequest

router = APIRouter()


def _period(
    days: int,
    date_from: date | None,
    date_to: date | None,
):
    try:
        return resolve_period(days=days, date_from=date_from, date_to=date_to)
    except InvalidDashboardPeriod as exc:
        raise bad_request(str(exc), code="invalid_dashboard_period") from exc


@router.get("/dashboard/bot", response_model=BotDashboardResponse)
def bot_dashboard(
    days: int = Query(default=30, ge=1, le=365),
    date_from: date | None = None,
    date_to: date | None = None,
    _: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
):
    if bot.id is None:
        raise bad_request("Bot context is incomplete", code="invalid_analytics_context")
    period, previous = _period(days, date_from, date_to)
    return GetBotDashboard(SqlAlchemyDashboardRepository(db)).execute(bot.id, period, previous)


@router.get("/dashboard/platform", response_model=PlatformDashboardResponse)
def platform_dashboard(
    days: int = Query(default=30, ge=1, le=365),
    date_from: date | None = None,
    date_to: date | None = None,
    include_inactive: bool = False,
    _: CurrentPrincipal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    period, previous = _period(days, date_from, date_to)
    return GetPlatformDashboard(SqlAlchemyDashboardRepository(db)).execute(
        period,
        previous,
        include_inactive=include_inactive,
    )


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
def create_event(
    payload: AnalyticsEventRequest,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> Response:
    if bot.id is None or principal.user_id is None:
        raise bad_request("Analytics actor context is incomplete", code="invalid_analytics_context")
    try:
        event = AnalyticsEvent(
            event_id=str(payload.event_id),
            session_id=str(payload.session_id),
            bot_instance_id=bot.id,
            user_id=principal.user_id,
            action_type=AnalyticsEventName(payload.action_type),
            source_surface=(SourceSurface(payload.source_surface) if payload.source_surface else None),
            interaction_kind=(
                ContentInteractionKind(payload.interaction_kind)
                if payload.interaction_kind
                else None
            ),
            category_id=payload.category_id,
            source_category_id=payload.source_category_id,
            content_version_id=payload.content_version_id,
            block_id=payload.block_id,
            item_id=payload.item_id,
            tabs_block_id=payload.tabs_block_id,
            tab_key=payload.tab_key,
            form_template_id=payload.form_template_id,
            form_version_id=payload.form_version_id,
            faq_id=payload.faq_id,
            attachment_id=payload.attachment_id,
            capability_installation_id=payload.capability_installation_id,
            capability_key=payload.capability_key,
            capability_view_key=payload.capability_view_key,
        )
        RecordAnalyticsEvent(SqlAlchemyAnalyticsEventRepository(db)).execute(event)
        db.commit()
    except InvalidAnalyticsEvent as exc:
        db.rollback()
        raise bad_request(str(exc), code="invalid_analytics_event") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
