from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal, require_student
from ....core.config import settings
from ....core.errors import bad_request, consent_required, forbidden, unauthorized
from ....core.security import create_access_token
from ....db.session import get_db
from ....services.log_action import ActionType, log_action
from ....services.max_validation import (
    InitDataValidationError,
    validate_contact,
    validate_init_data,
)
from ....services.push import enqueue_push
from ....services.rate_limit import enforce_rate_limit, max_user_rate_identity
from ...admins.infrastructure.models import Admin
from ...admins.presentation.schemas import AdminOut
from ...bot_instances.application.runtime_credentials import resolve_bot_token
from ...bot_instances.domain.entities import BotInstance
from ...bot_instances.infrastructure.env_file_credentials import EnvFileRuntimeCredentialStore
from ...bot_instances.infrastructure.runtime_repository import get_or_create_runtime
from ...consent.application.use_cases import AcceptConsent, CheckConsentGate
from ...consent.infrastructure.funnel import ConsentFunnelEvent, bump_consent_funnel
from ...consent.infrastructure.notice_repository import effective_policy_url
from ...consent.infrastructure.repositories import SqlAlchemyConsentRepository
from ...tenancy.presentation.dependencies import resolve_tenant
from ..application.services import EnsureBotMembership
from ..infrastructure.gateways import SqlAlchemyProfileGateway
from ..infrastructure.models import User
from .auth_schemas import ContactIn, ContactOut, InitDataIn, StudentLoginOut, StudentProfileOut, TokenOut

router = APIRouter()


def _make_token(payload: dict, *, expires_min: int | None = None) -> TokenOut:
    lifetime = expires_min or settings.JWT_EXPIRES_MIN
    token = create_access_token(payload, expires_min=lifetime)
    return TokenOut(
        access_token=token,
        token_type="bearer",
        role=payload["role"],
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=lifetime),
    )


def _resolve_system_token(db: Session, bot_id: int, system: str) -> str | None:
    """MAX signs `initData` per-bot; resolve the SPECIFIC bot's own token rather than a
    platform-wide default (Task 036 -- a global token only ever matched whichever one bot
    happened to own it, so every other bot's login/phone-verify silently failed)."""
    if system == "beavers":
        return settings.BEAVERS_BOT_TOKEN or None
    runtime = get_or_create_runtime(db, bot_id)
    if runtime is None:
        return None
    return resolve_bot_token(
        credential_source=runtime.credential_source,
        credential_env_key=runtime.credential_env_key,
        store=EnvFileRuntimeCredentialStore(settings.BOT_MANAGED_ENV_FILE),
        legacy_fallback_token=settings.MAX_BOT_TOKEN,
    )


@router.post(
    "/init-data/validate",
    response_model=StudentLoginOut,
)
def auth_inid_data_validate(
    payload: InitDataIn,
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
) -> StudentLoginOut:
    if bot.id is None:
        raise unauthorized("Экземпляр бота не найден")
    bot_token = _resolve_system_token(db, bot.id, payload.system.value)
    try:
        init = validate_init_data(payload.init_data, token=bot_token)
    except InitDataValidationError as e:
        raise unauthorized(str(e)) from e
    enforce_rate_limit(
        "auth_max",
        limit=60,
        window_seconds=60,
        tenant=bot.slug,
        identity=max_user_rate_identity(payload.system.value, init.user_id),
    )

    # Consent gate (Task 064) -- checked against the freshly re-validated MAX identity,
    # before any User row is looked up/created/refilled. `accept_consent` is the explicit
    # affirmative act from the gate screen's "Я согласен" button re-calling this same
    # endpoint; without it, an inactive identity gets no token and no row, only the signal
    # to render the gate. This also covers first-time contact and re-contact after a
    # completed erasure cycle -- there is no session to reuse in either case, only a
    # freshly signed initData.
    active = CheckConsentGate(SqlAlchemyConsentRepository(db)).execute(
        init.user_id, payload.system.value
    )
    if not active and not payload.accept_consent:
        bump_consent_funnel(db, bot.id, ConsentFunnelEvent.gate_shown)
        db.commit()
        raise consent_required(
            policy_url=effective_policy_url(),
            policy_version=settings.POLICY_VERSION,
        )

    user = db.execute(
        select(User).where(User.user_id == init.user_id, User.system == payload.system)
    ).scalar_one_or_none()

    if user is None:
        user = User(
            user_id=init.user_id,
            system=payload.system,
            first_name=init.first_name,
            last_name=init.last_name,
            username=init.username,
            photo_url=init.photo_url,
            language_code=init.language_code,
        )
        db.add(user)
        db.flush()
    else:
        user.username = init.username or user.username
        user.photo_url = init.photo_url or user.photo_url
        user.language_code = init.language_code or user.language_code
        if not user.first_name and init.first_name:
            user.first_name = init.first_name
        if not user.last_name and init.last_name:
            user.last_name = init.last_name

    db.flush()

    consent_state = None
    if not active:
        consent_state = AcceptConsent(SqlAlchemyConsentRepository(db)).execute(
            external_user_id=init.user_id,
            system=payload.system.value,
            user_id=user.id,
            policy_version=settings.POLICY_VERSION,
            now=datetime.now(tz=UTC),
        )
        bump_consent_funnel(db, bot.id, ConsentFunnelEvent.gate_accepted)

    membership = EnsureBotMembership(SqlAlchemyProfileGateway(db)).execute(bot.id, user.id)
    if not membership.is_active:
        raise forbidden("Доступ к этому боту отключён", code="membership_inactive")

    # Chat confirmation for a mini-app accept (Task 071) -- only after the membership check
    # passes, so a 403 on this same request rolls back the enqueued row along with the rest
    # of the transaction instead of leaving an orphaned push for a failed accept. Bot-chat
    # accept already confirms in place (main.py edits the existing message), so this is the
    # mini-app-only gap this task closes.
    if consent_state is not None and consent_state.given_at is not None:
        enqueue_push(
            db,
            bot_instance_id=bot.id,
            user_id=user.id,
            kind="consent_accepted",
            payload={"given_at": consent_state.given_at.isoformat()},
        )

    db.commit()
    db.refresh(user)

    token = _make_token(
        {
            "sub": f"u:{user.id}",
            "role": "student",
            "user_pk": user.id,
            "system": user.system.value,
            "bot_instance_id": bot.id,
            "bot_slug": bot.slug,
        }
    )
    return StudentLoginOut(token=token, user=StudentProfileOut.model_validate(user, from_attributes=True))


@router.post("/phone/verify", response_model=ContactOut)
def auth_phone_verify(
    payload: ContactIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_student),
) -> ContactOut:
    """Подтверждение телефона из MAX. Привязывает phone к текущему студенту."""
    user = db.get(User, p.user_id)
    if user is None:
        raise unauthorized("Студент не найден")
    if p.bot_instance_id is None:
        raise unauthorized("Экземпляр бота не найден")

    ok = validate_contact(
        phone=payload.phone,
        auth_date=payload.auth_date,
        user_id=user.user_id,
        received_hash=payload.hash,
        token=_resolve_system_token(db, p.bot_instance_id, payload.system.value),
    )
    if not ok:
        raise bad_request("Подпись контакта не совпадает", code="bad_contact_hash")

    user.phone = payload.phone
    user.phone_verified = True

    log_action(
        session=db,
        bot_instance_id=p.bot_instance_id,
        user_id=p.user_id,
        action_type=ActionType.SUBMIT_PHONE,
    )

    db.commit()
    return ContactOut(ok=True, phone=payload.phone, verified=True)


@router.get("/me")
def auth_me(
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(get_current_principal),
) -> dict:
    if p.role == "student" and p.user_id:
        user = db.get(User, p.user_id)
        if user is None:
            raise unauthorized("Пользователь не найден")
        return {
            "role": "student",
            "user": StudentProfileOut.model_validate(user, from_attributes=True).model_dump(),
        }
    if p.is_staff and p.admin_id:
        admin = db.get(Admin, p.admin_id)
        if admin is None:
            raise unauthorized("Админ не найден")
        return {
            "role": p.role,
            "admin": AdminOut.model_validate(admin, from_attributes=True).model_dump(),
        }
    raise unauthorized("Невозможно определить субъекта")
