from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .....api.deps import CurrentPrincipal, require_student
from .....core.errors import bad_request, not_found
from .....db.session import get_db
from .....modules.bot_instances.domain.entities import BotInstance
from .....modules.maintenance.presentation.dependencies import (
    enforce_user_access_available,
    enforce_user_write_available,
)
from .....modules.tenancy.presentation.dependencies import require_tenant_access
from .....services.log_action import ActionType, log_action
from .....services.rate_limit import rate_limit
from ...application.use_cases import CapabilityDisabled, CapabilityNotInstalled, GetEnabledCapability
from ...domain.entities import UnknownCapability
from ...infrastructure.catalog import capability_registry
from ...infrastructure.repositories import SqlAlchemyCapabilityInstallationRepository
from ..application.use_cases import (
    GetAdmissionRatingSubscription,
    LookupAdmissionRating,
    SetAdmissionRatingSubscription,
)
from ..domain.change_policy import competition_title
from ..domain.config import InvalidAdmissionRatingConfig, parse_admission_rating_config
from ..domain.identity import InvalidApplicantCode
from ..infrastructure.repositories import SqlAlchemyAdmissionRatingRepository
from .schemas import (
    RatingEntryResponse,
    RatingLookupResponse,
    RatingSubscriptionRequest,
    RatingSubscriptionResponse,
)

router = APIRouter()
_lookup_limit = rate_limit("capability_admission_rating_lookup", limit=30, window_seconds=60)


def _bot_id(bot: BotInstance) -> int:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    return bot.id


def _enabled(db: Session, bot_id: int):
    try:
        installation, _ = GetEnabledCapability(
            SqlAlchemyCapabilityInstallationRepository(db), capability_registry
        ).execute(bot_id, "admission_rating")
        assert installation.id is not None
        return installation, parse_admission_rating_config(installation.config)
    except (
        CapabilityNotInstalled,
        CapabilityDisabled,
        UnknownCapability,
        InvalidAdmissionRatingConfig,
    ) as exc:
        raise not_found("Capability is unavailable", code="capability_disabled") from exc


@router.get(
    "/lookup",
    response_model=RatingLookupResponse,
    dependencies=[Depends(_lookup_limit), Depends(enforce_user_access_available)],
)
def lookup(
    applicant_code: str = Query(min_length=1, max_length=64),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> RatingLookupResponse:
    bot_id = _bot_id(bot)
    installation, _ = _enabled(db, bot_id)
    try:
        result = LookupAdmissionRating(SqlAlchemyAdmissionRatingRepository(db)).execute(
            bot_instance_id=bot_id, user_id=principal.user_id, applicant_code=applicant_code
        )
    except InvalidApplicantCode as exc:
        raise bad_request(str(exc), code="invalid_applicant_code") from exc
    log_action(
        db,
        bot_instance_id=bot_id,
        user_id=principal.user_id,
        action_type=ActionType.CAPABILITY_LOOKUP_COMPLETE,
        capability_installation_id=installation.id,
        capability_key="admission_rating",
        capability_view_key="lookup",
        outcome_code="found" if result.entries else "not_found",
    )
    db.commit()
    return RatingLookupResponse(
        applicant_code=result.applicant_code,
        is_subscribed=result.is_subscribed,
        entries=[
            RatingEntryResponse(
                **{
                    "plan_id": item.plan_id,
                    "specialty": item.specialty,
                    "qualification": item.qualification,
                    "points": item.points,
                    "preference": item.preference,
                    "competition": competition_title(item.competition),
                    "group_name": item.group_name,
                    "position": item.position,
                    "total": item.total,
                    "checked_at": item.checked_at,
                }
            )
            for item in result.entries
        ],
    )


@router.get(
    "/subscription",
    response_model=RatingSubscriptionResponse,
    dependencies=[Depends(enforce_user_access_available)],
)
def subscription(
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> RatingSubscriptionResponse:
    bot_id = _bot_id(bot)
    _enabled(db, bot_id)
    current = GetAdmissionRatingSubscription(SqlAlchemyAdmissionRatingRepository(db)).execute(
        bot_id, principal.user_id
    )
    return RatingSubscriptionResponse(
        applicant_code=current.applicant_code if current else None, is_active=current is not None
    )


def _set(
    payload: RatingSubscriptionRequest,
    active: bool,
    principal: CurrentPrincipal,
    bot: BotInstance,
    db: Session,
) -> RatingSubscriptionResponse:
    bot_id = _bot_id(bot)
    installation, config = _enabled(db, bot_id)
    if active and not config.notifications_enabled:
        raise bad_request("Notifications are disabled", code="capability_notifications_disabled")
    try:
        saved = SetAdmissionRatingSubscription(SqlAlchemyAdmissionRatingRepository(db)).execute(
            bot_instance_id=bot_id,
            installation_id=installation.id,
            user_id=principal.user_id,
            applicant_code=payload.applicant_code,
            active=active,
        )
    except InvalidApplicantCode as exc:
        raise bad_request(str(exc), code="invalid_applicant_code") from exc
    log_action(
        db,
        bot_instance_id=bot_id,
        user_id=principal.user_id,
        action_type=ActionType.CAPABILITY_SUBSCRIPTION_CHANGED,
        capability_installation_id=installation.id,
        capability_key="admission_rating",
        outcome_code="enabled" if active else "disabled",
    )
    db.commit()
    return RatingSubscriptionResponse(applicant_code=saved.applicant_code, is_active=saved.is_active)


@router.post(
    "/subscribe",
    response_model=RatingSubscriptionResponse,
    dependencies=[Depends(enforce_user_write_available)],
)
def subscribe(
    payload: RatingSubscriptionRequest,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> RatingSubscriptionResponse:
    return _set(payload, True, principal, bot, db)


@router.post(
    "/unsubscribe",
    response_model=RatingSubscriptionResponse,
    dependencies=[Depends(enforce_user_write_available)],
)
def unsubscribe(
    payload: RatingSubscriptionRequest,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> RatingSubscriptionResponse:
    return _set(payload, False, principal, bot, db)
