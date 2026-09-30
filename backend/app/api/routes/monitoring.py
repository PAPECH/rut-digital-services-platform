"""Deprecated compatibility adapter for the request-status capability."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...modules.bot_instances.domain.entities import BotInstance
from ...modules.capabilities.request_status.presentation.router import (
    lookup as capability_lookup,
)
from ...modules.capabilities.request_status.presentation.router import (
    subscribe as capability_subscribe,
)
from ...modules.capabilities.request_status.presentation.router import (
    subscription as capability_subscription,
)
from ...modules.capabilities.request_status.presentation.router import (
    unsubscribe as capability_unsubscribe,
)
from ...modules.capabilities.request_status.presentation.schemas import (
    RequestStatusSubscriptionRequest,
)
from ...modules.maintenance.presentation.dependencies import (
    enforce_user_access_available,
    enforce_user_write_available,
)
from ...modules.tenancy.presentation.dependencies import require_tenant_access
from ...schemas.monitoring import LookupOut, SubscribeIn, SubscribeOut, SubscriptionOut
from ...services.rate_limit import rate_limit
from ..deps import CurrentPrincipal, require_student

router = APIRouter()
_lookup_limit = rate_limit("monitoring_lookup", limit=30, window_seconds=60)


@router.get(
    "/lookup",
    response_model=LookupOut,
    dependencies=[Depends(_lookup_limit), Depends(enforce_user_access_available)],
    deprecated=True,
)
def lookup(
    request_number: str = Query(min_length=1, max_length=64),
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> LookupOut:
    result = capability_lookup(request_number, principal, bot, db)
    return LookupOut(**result.model_dump())


@router.get(
    "/subscription",
    response_model=SubscriptionOut,
    dependencies=[Depends(enforce_user_access_available)],
    deprecated=True,
)
def my_subscription(
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> SubscriptionOut:
    result = capability_subscription(principal, bot, db)
    return SubscriptionOut(**result.model_dump())


@router.post(
    "/subscribe",
    response_model=SubscribeOut,
    dependencies=[Depends(enforce_user_write_available)],
    deprecated=True,
)
def subscribe(
    payload: SubscribeIn,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> SubscribeOut:
    result = capability_subscribe(
        RequestStatusSubscriptionRequest(request_number=payload.request_number),
        principal,
        bot,
        db,
    )
    return SubscribeOut(request_number=result.request_number or "", is_active=result.is_active)


@router.post(
    "/unsubscribe",
    response_model=SubscribeOut,
    dependencies=[Depends(enforce_user_write_available)],
    deprecated=True,
)
def unsubscribe(
    payload: SubscribeIn,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> SubscribeOut:
    result = capability_unsubscribe(
        RequestStatusSubscriptionRequest(request_number=payload.request_number),
        principal,
        bot,
        db,
    )
    return SubscribeOut(request_number=result.request_number or "", is_active=result.is_active)
