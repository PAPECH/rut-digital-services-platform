from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .....api.deps import CurrentPrincipal, require_student
from .....core.errors import bad_request, not_found, service_unavailable
from .....db.session import get_db
from .....modules.bot_instances.domain.entities import BotInstance
from .....modules.maintenance.presentation.dependencies import (
    enforce_user_access_available,
    enforce_user_write_available,
)
from .....modules.tenancy.presentation.dependencies import require_tenant_access
from .....services.log_action import ActionType, log_action
from .....services.rate_limit import rate_limit
from ...application.use_cases import (
    CapabilityDisabled,
    CapabilityNotInstalled,
    GetEnabledCapability,
)
from ...domain.entities import UnknownCapability
from ...infrastructure.catalog import capability_registry
from ...infrastructure.repositories import SqlAlchemyCapabilityInstallationRepository
from ..application.use_cases import (
    GetRequestStatusSubscription,
    LookupRequestStatus,
    RequestStatusProviderUnavailable,
    SetRequestStatusSubscription,
)
from ..domain.config import InvalidRequestStatusConfig, parse_request_status_config
from ..domain.identity import InvalidRequestNumber, request_number_hash
from ..infrastructure.provider import GoogleSheetsStatusProvider
from ..infrastructure.repositories import SqlAlchemyRequestStatusRepository
from .schemas import (
    RequestStatusLookupResponse,
    RequestStatusSubscriptionRequest,
    RequestStatusSubscriptionResponse,
)

router = APIRouter()
_lookup_limit = rate_limit("capability_request_status_lookup", limit=30, window_seconds=60)


def _bot_id(bot: BotInstance) -> int:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    return bot.id


def _enabled(db: Session, bot_instance_id: int):
    try:
        installation, _ = GetEnabledCapability(
            SqlAlchemyCapabilityInstallationRepository(db),
            capability_registry,
        ).execute(bot_instance_id, "request_status")
        assert installation.id is not None
        return installation, parse_request_status_config(installation.config)
    except (CapabilityNotInstalled, CapabilityDisabled, UnknownCapability, InvalidRequestStatusConfig) as exc:
        raise not_found(
            "Capability is unavailable",
            code="capability_disabled",
        ) from exc


def _lookup_response(result) -> RequestStatusLookupResponse:
    return RequestStatusLookupResponse(
        request_number=result.request_number,
        status=result.status,
        checked_at=result.checked_at,
        is_subscribed=result.is_subscribed,
    )


@router.get(
    "/lookup",
    response_model=RequestStatusLookupResponse,
    dependencies=[Depends(_lookup_limit), Depends(enforce_user_access_available)],
)
def lookup(
    request_number: str = Query(min_length=1, max_length=64),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> RequestStatusLookupResponse:
    bot_id = _bot_id(bot)
    installation, config = _enabled(db, bot_id)
    repository = SqlAlchemyRequestStatusRepository(db)
    try:
        result = LookupRequestStatus(
            repository,
            GoogleSheetsStatusProvider(circuit_key=f"{bot_id}:{installation.id}"),
        ).execute(
            bot_instance_id=bot_id,
            installation_id=installation.id,
            user_id=principal.user_id,
            request_number=request_number,
            config=config,
        )
        log_action(
            db,
            bot_instance_id=bot_id,
            user_id=principal.user_id,
            action_type=ActionType.CAPABILITY_LOOKUP_COMPLETE,
            capability_installation_id=installation.id,
            capability_key="request_status",
            capability_view_key="lookup",
            outcome_code="found" if result.status is not None else "not_found",
        )
        db.commit()
    except RequestStatusProviderUnavailable as exc:
        db.rollback()
        log_action(
            db,
            bot_instance_id=bot_id,
            user_id=principal.user_id,
            action_type=ActionType.CAPABILITY_LOOKUP_COMPLETE,
            capability_installation_id=installation.id,
            capability_key="request_status",
            capability_view_key="lookup",
            outcome_code="provider_error",
            commit=True,
        )
        raise service_unavailable(
            "Status provider is temporarily unavailable",
            code="capability_provider_unavailable",
        ) from exc
    except InvalidRequestNumber as exc:
        db.rollback()
        raise bad_request(str(exc), code="invalid_request_number") from exc
    return _lookup_response(result)


@router.get(
    "/subscription",
    response_model=RequestStatusSubscriptionResponse,
    dependencies=[Depends(enforce_user_access_available)],
)
def subscription(
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> RequestStatusSubscriptionResponse:
    bot_id = _bot_id(bot)
    _enabled(db, bot_id)
    repository = SqlAlchemyRequestStatusRepository(db)
    current = GetRequestStatusSubscription(repository).execute(bot_id, principal.user_id)
    if current is None:
        return RequestStatusSubscriptionResponse(is_active=False)
    state = repository.get_state(
        bot_id,
        request_number_hash(bot_id, current.request_number),
    )
    return RequestStatusSubscriptionResponse(
        request_number=current.request_number,
        is_active=True,
        last_status=state.last_status if state else None,
        checked_at=state.checked_at if state else None,
    )


def _set_subscription(
    *,
    payload: RequestStatusSubscriptionRequest,
    active: bool,
    principal: CurrentPrincipal,
    bot: BotInstance,
    db: Session,
) -> RequestStatusSubscriptionResponse:
    bot_id = _bot_id(bot)
    installation, config = _enabled(db, bot_id)
    if active and not config.notifications_enabled:
        raise bad_request(
            "Notifications are disabled for this capability",
            code="capability_notifications_disabled",
        )
    try:
        saved = SetRequestStatusSubscription(SqlAlchemyRequestStatusRepository(db)).execute(
            bot_instance_id=bot_id,
            installation_id=installation.id,
            user_id=principal.user_id,
            request_number=payload.request_number,
            config=config,
            active=active,
        )
        log_action(
            db,
            bot_instance_id=bot_id,
            user_id=principal.user_id,
            action_type=ActionType.CAPABILITY_SUBSCRIPTION_CHANGED,
            capability_installation_id=installation.id,
            capability_key="request_status",
            outcome_code="enabled" if active else "disabled",
        )
        db.commit()
    except InvalidRequestNumber as exc:
        db.rollback()
        raise bad_request(str(exc), code="invalid_request_number") from exc
    return RequestStatusSubscriptionResponse(
        request_number=saved.request_number,
        is_active=saved.is_active,
    )


@router.post(
    "/subscribe",
    response_model=RequestStatusSubscriptionResponse,
    dependencies=[Depends(enforce_user_write_available)],
)
def subscribe(
    payload: RequestStatusSubscriptionRequest,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> RequestStatusSubscriptionResponse:
    return _set_subscription(
        payload=payload,
        active=True,
        principal=principal,
        bot=bot,
        db=db,
    )


@router.post(
    "/unsubscribe",
    response_model=RequestStatusSubscriptionResponse,
    dependencies=[Depends(enforce_user_write_available)],
)
def unsubscribe(
    payload: RequestStatusSubscriptionRequest,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> RequestStatusSubscriptionResponse:
    return _set_subscription(
        payload=payload,
        active=False,
        principal=principal,
        bot=bot,
        db=db,
    )
