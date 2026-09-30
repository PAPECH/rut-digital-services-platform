from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_student
from ....core.errors import bad_request, not_found
from ....db.session import get_db
from ....services.log_action import ActionType, log_action
from ....services.rate_limit import rate_limit
from ...bot_instances.domain.entities import BotInstance
from ...consent.application.use_cases import GetConsentStatus
from ...consent.infrastructure.notice_repository import effective_policy_url
from ...consent.infrastructure.repositories import SqlAlchemyConsentRepository
from ...maintenance.presentation.dependencies import enforce_user_write_available
from ...tenancy.presentation.dependencies import require_tenant_access
from ..application.dto import UpdateBotProfileCommand
from ..application.use_cases import (
    GetBotProfile,
    ProfileFieldNotConfigured,
    ProfileNotFound,
    UpdateBotProfile,
)
from ..domain.fields import InvalidProfileField
from ..infrastructure.gateways import SqlAlchemyProfileGateway
from ..infrastructure.models import User
from .schemas import ProfileResponse, ProfileUpdateRequest, RutLinkResponse

router = APIRouter()
_profile_rl = rate_limit("profile_update", limit=30, window_seconds=60)


def _response(db: Session, user_id: int, profile) -> ProfileResponse:
    record = db.get(User, user_id)
    if record is None:
        raise not_found("Профиль не найден")
    consent = GetConsentStatus(SqlAlchemyConsentRepository(db)).execute(
        record.user_id, record.system.value
    )
    return ProfileResponse.from_profile(
        profile, record, consent, policy_url=effective_policy_url()
    )


@router.get("", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> ProfileResponse:
    try:
        profile = GetBotProfile(SqlAlchemyProfileGateway(db)).execute(bot.id, principal.user_id)
    except ProfileNotFound as exc:
        raise not_found("Профиль не найден") from exc
    return _response(db, principal.user_id, profile)


@router.put(
    "",
    response_model=ProfileResponse,
    dependencies=[Depends(_profile_rl), Depends(enforce_user_write_available)],
)
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> ProfileResponse:
    try:
        profile = UpdateBotProfile(SqlAlchemyProfileGateway(db)).execute(
            bot.id,
            principal.user_id,
            bot.profile_schema,
            UpdateBotProfileCommand(**payload.model_dump()),
        )
    except ProfileNotFound as exc:
        raise not_found("Профиль не найден") from exc
    except ProfileFieldNotConfigured as exc:
        raise bad_request(
            "Поле профиля не настроено для этого бота",
            code="profile_field_not_configured",
            field_key=str(exc),
        ) from exc
    except InvalidProfileField as exc:
        raise bad_request(str(exc), code="invalid_profile_field") from exc

    log_action(
        session=db,
        bot_instance_id=bot.id,
        user_id=principal.user_id,
        action_type=ActionType.PROFILE_UPDATED,
    )
    db.commit()
    return _response(db, principal.user_id, profile)


@router.post("/rut/link", response_model=RutLinkResponse)
def link_rut(_: CurrentPrincipal = Depends(require_student)) -> RutLinkResponse:
    return RutLinkResponse()
