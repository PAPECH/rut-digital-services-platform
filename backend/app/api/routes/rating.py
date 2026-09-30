"""Deprecated compatibility adapter for the admission-rating capability."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...modules.bot_instances.domain.entities import BotInstance
from ...modules.capabilities.admission_rating.presentation.router import (
    lookup as capability_lookup,
)
from ...modules.capabilities.admission_rating.presentation.router import (
    subscribe as capability_subscribe,
)
from ...modules.capabilities.admission_rating.presentation.router import (
    subscription as capability_subscription,
)
from ...modules.capabilities.admission_rating.presentation.router import (
    unsubscribe as capability_unsubscribe,
)
from ...modules.capabilities.admission_rating.presentation.schemas import (
    RatingSubscriptionRequest,
)
from ...modules.maintenance.presentation.dependencies import (
    enforce_user_access_available,
    enforce_user_write_available,
)
from ...modules.tenancy.presentation.dependencies import require_tenant_access
from ...schemas.admission import (
    RatingEntryOut,
    RatingLookupOut,
    RatingSubscribeIn,
    RatingSubscribeOut,
    RatingSubscriptionOut,
)
from ...services.rate_limit import rate_limit
from ..deps import CurrentPrincipal, require_student

router = APIRouter(deprecated=True)
_lookup_limit = rate_limit("rating_lookup_compatibility", limit=30, window_seconds=60)


def _legacy_entry(code: str, entry) -> RatingEntryOut:
    return RatingEntryOut(
        plan_id=entry.plan_id,
        display_name=code,
        spec_display_name=entry.specialty,
        spec_qualifier=entry.qualification,
        points=entry.points,
        preference_index_display=entry.preference,
        competition_name=entry.competition,
        group_name=entry.group_name,
        rating_index=entry.position,
        checked_at=entry.checked_at,
        total=entry.total,
    )


@router.get(
    "/lookup",
    response_model=RatingLookupOut,
    dependencies=[Depends(_lookup_limit), Depends(enforce_user_access_available)],
)
def lookup(
    display_name: str = Query(...),
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> RatingLookupOut:
    result = capability_lookup(display_name, principal, bot, db)
    return RatingLookupOut(
        display_name=result.applicant_code,
        entries=[_legacy_entry(result.applicant_code, entry) for entry in result.entries],
        is_subscribed=result.is_subscribed,
    )


@router.get(
    "/subscription",
    response_model=RatingSubscriptionOut,
    dependencies=[Depends(enforce_user_access_available)],
)
def subscription(
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> RatingSubscriptionOut:
    current = capability_subscription(principal, bot, db)
    if not current.is_active or not current.applicant_code:
        return RatingSubscriptionOut(is_active=False)
    result = capability_lookup(current.applicant_code, principal, bot, db)
    return RatingSubscriptionOut(
        display_name=current.applicant_code,
        is_active=True,
        entries=[_legacy_entry(current.applicant_code, entry) for entry in result.entries],
    )


@router.post(
    "/subscribe",
    response_model=RatingSubscribeOut,
    dependencies=[Depends(enforce_user_write_available)],
)
def subscribe(
    payload: RatingSubscribeIn,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> RatingSubscribeOut:
    result = capability_subscribe(
        RatingSubscriptionRequest(applicant_code=payload.display_name), principal, bot, db
    )
    return RatingSubscribeOut(display_name=result.applicant_code or "", is_active=result.is_active)


@router.post(
    "/unsubscribe",
    response_model=RatingSubscribeOut,
    dependencies=[Depends(enforce_user_write_available)],
)
def unsubscribe(
    payload: RatingSubscribeIn,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> RatingSubscribeOut:
    result = capability_unsubscribe(
        RatingSubscriptionRequest(applicant_code=payload.display_name), principal, bot, db
    )
    return RatingSubscribeOut(display_name=result.applicant_code or "", is_active=result.is_active)
