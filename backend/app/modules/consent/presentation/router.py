from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_platform_admin, require_student
from ....core.config import settings
from ....db.session import get_db
from ....services.bot_runtime_auth import authorize_bot_runtime
from ....services.push import enqueue_push
from ....services.rate_limit import enforce_rate_limit, max_user_rate_identity
from ...bot_instances.domain.entities import BotInstance
from ...profiles.infrastructure.models import User
from ...tenancy.presentation.dependencies import resolve_tenant
from ..application.use_cases import AcceptConsent, CheckConsentGate, GetConsentStatus, RevokeConsent
from ..infrastructure.models import ConsentEventRecord, UserConsentRecord
from ..infrastructure.notice_repository import (
    POLICY_DOCUMENT_HTML_KEY,
    SqlAlchemyConsentNoticeRepository,
    effective_policy_url,
    render_policy_document_page,
)
from ..infrastructure.repositories import SqlAlchemyConsentRepository
from .schemas import (
    ConsentBotIdentityIn,
    ConsentEventOut,
    ConsentNoticeIn,
    ConsentNoticeOut,
    ConsentStatusOut,
    ErasureRegisterEntryOut,
    PolicyDocumentContentOut,
    PolicyDocumentHtmlIn,
)

router = APIRouter()

_NOTICE_LANGS = ("ru", "en")


def _status_out(state) -> ConsentStatusOut:
    return ConsentStatusOut.from_state(state, policy_url=effective_policy_url())


# --- Student (mini-app) channel -------------------------------------------------------
#
# Covers re-accept/revoke while a session already exists (a `User` row is present and the
# JWT is still valid -- true throughout the 10-business-day grace window after revoke). The
# *first* accept, and accept after a completed erasure cycle, happen inline in
# `/auth/init-data/validate` instead (see profiles/presentation/auth_router.py) because
# there is no session yet at that point -- identity there comes from freshly re-validated
# MAX initData, not a bearer token.


@router.post("/accept", response_model=ConsentStatusOut)
def accept_consent(
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_student),
) -> ConsentStatusOut:
    user = db.get(User, p.user_id) if p.user_id else None
    if user is None:
        return _status_out(None)
    repo = SqlAlchemyConsentRepository(db)
    was_active = CheckConsentGate(repo).execute(user.user_id, user.system.value)
    state = AcceptConsent(repo).execute(
        external_user_id=user.user_id,
        system=user.system.value,
        user_id=user.id,
        policy_version=settings.POLICY_VERSION,
        now=datetime.now(tz=UTC),
    )
    # Chat confirmation for a mini-app re-accept during the revoke grace window (Task 071) --
    # only on a genuine inactive -> active transition, matching AcceptConsent's own
    # idempotency check, so re-tapping an already-active accept doesn't send a second message.
    if not was_active and state is not None and state.given_at is not None and p.bot_instance_id:
        enqueue_push(
            db,
            bot_instance_id=p.bot_instance_id,
            user_id=user.id,
            kind="consent_accepted",
            payload={"given_at": state.given_at.isoformat()},
        )
    db.commit()
    return _status_out(state)


@router.post("/revoke", response_model=ConsentStatusOut)
def revoke_consent(
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_student),
) -> ConsentStatusOut:
    user = db.get(User, p.user_id) if p.user_id else None
    if user is None:
        return _status_out(None)
    state = RevokeConsent(SqlAlchemyConsentRepository(db)).execute(
        external_user_id=user.user_id, system=user.system.value, now=datetime.now(tz=UTC)
    )
    db.commit()
    return _status_out(state)


@router.get("/status", response_model=ConsentStatusOut)
def get_consent_status(
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_student),
) -> ConsentStatusOut:
    user = db.get(User, p.user_id) if p.user_id else None
    if user is None:
        return _status_out(None)
    state = GetConsentStatus(SqlAlchemyConsentRepository(db)).execute(user.user_id, user.system.value)
    return _status_out(state)


# --- Bot channel ------------------------------------------------------------------------
#
# Mirrors /messages/ingress's auth shape exactly (resolve_tenant + bot-runtime token
# headers). Deliberately does not create/touch a `User` row -- it only records consent;
# the next ordinary message re-enters the normal ingress flow, which creates the row now
# that the gate reads active.


def _authorize_bot(
    db: Session, bot: BotInstance, x_bot_token: str | None, x_bot_runtime_token: str | None
) -> None:
    if bot.id is None:
        from ....core.errors import not_found

        raise not_found("Бот не найден", code="bot_not_found")
    authorize_bot_runtime(db, bot.id, x_bot_runtime_token, x_bot_token)


@router.post("/bot/status", response_model=ConsentStatusOut)
def bot_consent_status(
    payload: ConsentBotIdentityIn,
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    x_bot_token: str | None = Header(default=None, alias="X-Bot-Token"),
    x_bot_runtime_token: str | None = Header(default=None, alias="X-Bot-Runtime-Token"),
) -> ConsentStatusOut:
    _authorize_bot(db, bot, x_bot_token, x_bot_runtime_token)
    state = GetConsentStatus(SqlAlchemyConsentRepository(db)).execute(
        payload.user_id, payload.system.value
    )
    return _status_out(state)


@router.post("/bot/accept", response_model=ConsentStatusOut)
def bot_accept_consent(
    payload: ConsentBotIdentityIn,
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    x_bot_token: str | None = Header(default=None, alias="X-Bot-Token"),
    x_bot_runtime_token: str | None = Header(default=None, alias="X-Bot-Runtime-Token"),
) -> ConsentStatusOut:
    _authorize_bot(db, bot, x_bot_token, x_bot_runtime_token)
    assert bot.id is not None
    enforce_rate_limit(
        "consent_bot_accept",
        limit=20,
        window_seconds=60,
        tenant=bot.slug,
        identity=max_user_rate_identity(payload.system.value, payload.user_id),
    )
    state = AcceptConsent(SqlAlchemyConsentRepository(db)).execute(
        external_user_id=payload.user_id,
        system=payload.system.value,
        user_id=None,
        policy_version=settings.POLICY_VERSION,
        now=datetime.now(tz=UTC),
    )
    db.commit()
    return _status_out(state)


@router.post("/bot/revoke", response_model=ConsentStatusOut)
def bot_revoke_consent(
    payload: ConsentBotIdentityIn,
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    x_bot_token: str | None = Header(default=None, alias="X-Bot-Token"),
    x_bot_runtime_token: str | None = Header(default=None, alias="X-Bot-Runtime-Token"),
) -> ConsentStatusOut:
    _authorize_bot(db, bot, x_bot_token, x_bot_runtime_token)
    assert bot.id is not None
    enforce_rate_limit(
        "consent_bot_revoke",
        limit=20,
        window_seconds=60,
        tenant=bot.slug,
        identity=max_user_rate_identity(payload.system.value, payload.user_id),
    )
    state = RevokeConsent(SqlAlchemyConsentRepository(db)).execute(
        external_user_id=payload.user_id, system=payload.system.value, now=datetime.now(tz=UTC)
    )
    db.commit()
    return _status_out(state)


# --- Consent notice text (platform-wide, admin-editable) --------------------------------
#
# Not part of `bot_instances`' app_settings (that table hard-requires a bot_instance_id) --
# consent, like the notice text prompting for it, is the same across every bot. Read is
# deliberately public (only `resolve_tenant`, no bot-runtime token, no session/Bearer) --
# this exact text is what an anonymous, not-yet-consented person is shown before any
# identity or session exists (bot chat *and* the mini-app's pre-login gate), the same
# trust level as GET /manifest. There's nothing to protect: it's admin-authored display
# copy, not tenant data.


@router.get("/notice/{lang}", response_model=ConsentNoticeOut)
def get_consent_notice(
    lang: str,
    _: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
) -> ConsentNoticeOut:
    value = SqlAlchemyConsentNoticeRepository(db).get(lang) if lang in _NOTICE_LANGS else None
    return ConsentNoticeOut(key=lang, value=value)


@router.get("/admin/notice", response_model=list[ConsentNoticeOut])
def list_consent_notices(
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> list[ConsentNoticeOut]:
    values = SqlAlchemyConsentNoticeRepository(db).list_all()
    return [ConsentNoticeOut(key=lang, value=values.get(lang)) for lang in _NOTICE_LANGS]


@router.put("/admin/notice/{lang}", response_model=ConsentNoticeOut)
def put_consent_notice(
    lang: str,
    payload: ConsentNoticeIn,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> ConsentNoticeOut:
    if lang not in _NOTICE_LANGS:
        from ....core.errors import bad_request

        raise bad_request(f"Unsupported language: {lang}", code="unsupported_language")
    value = SqlAlchemyConsentNoticeRepository(db).upsert(lang, payload.value)
    db.commit()
    return ConsentNoticeOut(key=lang, value=value)


# --- Policy document (platform-wide, admin-editable HTML, rendered on our own page) --------
#
# Reuses the same consent_notice_texts key/value table as the notice text above rather than a
# dedicated table -- see notice_repository.py. No external URL, no uploaded file (an earlier
# iteration of this same session tried both -- URL-or-file toggle, then an uploaded PDF served
# from our own storage -- and dropped them: an uploaded file needs a correct Content-Type to
# open reliably, and MAX's own in-app "_blank" target turned out not to render one at all
# (blank screen, only a real address-bar navigation worked); a plain admin-authored HTML page
# we render ourselves sidesteps both problems entirely). The page route is deliberately public
# and takes no parameters -- it always renders whatever policy_document_html currently holds,
# never caller-supplied content, and must work with no Authorization header since bot chat
# clients and browsers open it directly (see effective_policy_url()'s docstring).


@router.get("/policy-document", response_class=HTMLResponse)
def get_policy_document_page(db: Session = Depends(get_db)) -> HTMLResponse:
    html = SqlAlchemyConsentNoticeRepository(db).get(POLICY_DOCUMENT_HTML_KEY)
    return HTMLResponse(render_policy_document_page(html))


@router.get("/policy-document/content", response_model=PolicyDocumentContentOut)
def get_policy_document_content(
    _: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
) -> PolicyDocumentContentOut:
    """Raw HTML (no page shell) for the mini-app's in-app policy screen -- same admin-authored
    value as the page above, unwrapped so it can be embedded directly via
    dangerouslySetInnerHTML rather than opened as a standalone document. `value` is `None`
    (not the placeholder text) when unset, same shape as GET /consent/notice/{lang}, so the
    caller can render its own localized/styled empty state."""
    value = SqlAlchemyConsentNoticeRepository(db).get(POLICY_DOCUMENT_HTML_KEY)
    return PolicyDocumentContentOut(value=value)


@router.get("/admin/policy-document", response_model=PolicyDocumentHtmlIn)
def get_policy_document_html(
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> PolicyDocumentHtmlIn:
    value = SqlAlchemyConsentNoticeRepository(db).get(POLICY_DOCUMENT_HTML_KEY)
    return PolicyDocumentHtmlIn(value=value or "")


@router.put("/admin/policy-document", response_model=PolicyDocumentHtmlIn)
def set_policy_document_html(
    payload: PolicyDocumentHtmlIn,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> PolicyDocumentHtmlIn:
    value = SqlAlchemyConsentNoticeRepository(db).upsert(POLICY_DOCUMENT_HTML_KEY, payload.value)
    db.commit()
    return PolicyDocumentHtmlIn(value=value)


# --- Platform-admin erasure register ------------------------------------------------------
#
# Platform-admin only, not bot-scoped -- there is no bot_instance_id left to scope by once
# the identity's bot_memberships are gone (see docs/tasks/064, Tenant-isolation rules).


@router.get("/admin/erasures", response_model=list[ErasureRegisterEntryOut])
def list_erasures(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> list[ErasureRegisterEntryOut]:
    rows = list(
        db.execute(
            select(UserConsentRecord)
            .where(UserConsentRecord.deleted_at.is_not(None))
            .order_by(UserConsentRecord.deleted_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars()
    )
    if not rows:
        return []
    events_by_consent: dict[int, list[ConsentEventRecord]] = {row.id: [] for row in rows}
    for event in db.execute(
        select(ConsentEventRecord)
        .where(ConsentEventRecord.user_consent_id.in_(events_by_consent))
        .order_by(ConsentEventRecord.occurred_at.asc())
    ).scalars():
        events_by_consent[event.user_consent_id].append(event)
    return [
        ErasureRegisterEntryOut(
            external_user_id=row.external_user_id,
            system=row.system.value,
            given_at=row.given_at,
            revoked_at=row.revoked_at,
            deleted_at=row.deleted_at,
            events=[
                ConsentEventOut(
                    event_type=e.event_type.value, occurred_at=e.occurred_at, policy_version=e.policy_version
                )
                for e in events_by_consent[row.id]
            ],
        )
        for row in rows
    ]
