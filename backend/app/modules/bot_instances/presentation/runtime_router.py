from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_platform_admin
from ....core.config import settings
from ....core.errors import bad_request, not_found
from ....db.session import get_db
from ....services.bot_runtime_auth import (
    authorize_bot_runtime,
    authorize_bot_supervisor,
    hash_runtime_token,
)
from ...tenancy.presentation.dependencies import resolve_tenant
from ..application.runtime_credentials import (
    ManagedBotTokenMissing,
    ProvisionManagedCredential,
    ProvisionManagedCredentialCommand,
    resolve_bot_token,
)
from ..domain.entities import BotInstance
from ..domain.runtime_credentials import InvalidBotCredential
from ..infrastructure.env_file_credentials import EnvFileRuntimeCredentialStore
from ..infrastructure.models import BotInstanceRecord, BotRuntimeRecord
from ..infrastructure.runtime_repository import get_or_create_runtime
from .runtime_schemas import (
    BotProcessManifestItem,
    RuntimeCredentialRequest,
    RuntimeHeartbeatRequest,
    RuntimePatchRequest,
    RuntimeResponse,
    RuntimeTokenResponse,
)

router = APIRouter()


def _get_or_create(db: Session, bot_id: int) -> BotRuntimeRecord:
    runtime = get_or_create_runtime(db, bot_id)
    if runtime is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    return runtime


def _credential_store() -> EnvFileRuntimeCredentialStore:
    return EnvFileRuntimeCredentialStore(settings.BOT_MANAGED_ENV_FILE)


def _response(
    runtime: BotRuntimeRecord,
    store: EnvFileRuntimeCredentialStore | None = None,
) -> RuntimeResponse:
    now = datetime.now(tz=timezone.utc)
    last_seen = runtime.last_seen_at
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    if runtime.last_error_code:
        status = "error"
    elif last_seen and last_seen >= now - timedelta(minutes=3):
        status = "online"
    elif runtime.last_seen_at:
        status = "offline"
    else:
        status = "not_connected"
    credential_source = runtime.credential_source
    if credential_source not in {"environment", "managed"}:
        credential_source = "environment" if runtime.credential_env_key else None
    credential_store = store or _credential_store()
    bot_token_configured = bool(
        resolve_bot_token(
            credential_source=credential_source,
            credential_env_key=runtime.credential_env_key,
            store=credential_store,
            legacy_fallback_token=settings.MAX_BOT_TOKEN,
        )
    )
    return RuntimeResponse(
        bot_instance_id=runtime.bot_instance_id,
        credential_source=credential_source,
        credential_env_key=runtime.credential_env_key,
        mode=runtime.mode,
        bot_token_configured=bot_token_configured,
        token_configured=bool(runtime.runtime_token_hash),
        status=status,
        last_seen_at=last_seen,
        username=runtime.username,
        max_bot_id=runtime.max_bot_id,
        runtime_version=runtime.runtime_version,
        last_error_code=runtime.last_error_code,
    )


@router.get("/{bot_id}/runtime", response_model=RuntimeResponse)
def get_runtime(
    bot_id: int,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> RuntimeResponse:
    runtime = _get_or_create(db, bot_id)
    db.commit()
    return _response(runtime)


@router.patch("/{bot_id}/runtime", response_model=RuntimeResponse)
def patch_runtime(
    bot_id: int,
    payload: RuntimePatchRequest,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> RuntimeResponse:
    runtime = _get_or_create(db, bot_id)
    runtime.credential_env_key = payload.credential_env_key or None
    runtime.credential_source = "environment" if runtime.credential_env_key else None
    runtime.mode = payload.mode
    db.commit()
    db.refresh(runtime)
    return _response(runtime)


@router.put("/{bot_id}/runtime/credential", response_model=RuntimeResponse)
def configure_runtime_credential(
    bot_id: int,
    payload: RuntimeCredentialRequest,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> RuntimeResponse:
    runtime = _get_or_create(db, bot_id)
    bot = db.get(BotInstanceRecord, bot_id)
    if bot is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    store = _credential_store()
    if payload.source == "environment":
        runtime.credential_source = "environment"
        runtime.credential_env_key = payload.credential_env_key
    else:
        try:
            provisioned = ProvisionManagedCredential(store).execute(
                ProvisionManagedCredentialCommand(
                    bot_slug=bot.slug,
                    bot_token=(
                        payload.bot_token.get_secret_value()
                        if payload.bot_token is not None
                        else None
                    ),
                    mode=payload.mode,
                )
            )
        except (InvalidBotCredential, ManagedBotTokenMissing) as exc:
            raise bad_request(str(exc), code="invalid_bot_credential") from exc
        runtime.credential_source = "managed"
        runtime.credential_env_key = provisioned.credential_env_key
        runtime.runtime_token_hash = hash_runtime_token(provisioned.runtime_token)
        runtime.last_seen_at = None
        runtime.last_error_code = None
    runtime.mode = payload.mode
    db.commit()
    db.refresh(runtime)
    return _response(runtime, store)


@router.post("/{bot_id}/runtime/rotate-token", response_model=RuntimeTokenResponse)
def rotate_runtime_token(
    bot_id: int,
    response: Response,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> RuntimeTokenResponse:
    runtime = _get_or_create(db, bot_id)
    if runtime.credential_source == "managed":
        raise bad_request(
            "Managed connection rotates its runtime token when saved",
            code="managed_runtime_token",
        )
    token = secrets.token_urlsafe(32)
    runtime.runtime_token_hash = hash_runtime_token(token)
    runtime.last_seen_at = None
    runtime.last_error_code = None
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return RuntimeTokenResponse(runtime_token=token)


@router.get("/runtime/processes", response_model=list[BotProcessManifestItem])
def process_manifest(
    db: Session = Depends(get_db),
    x_bot_token: str | None = Header(default=None, alias="X-Bot-Token"),
) -> list[BotProcessManifestItem]:
    authorize_bot_supervisor(x_bot_token)
    rows = db.execute(
        select(BotInstanceRecord, BotRuntimeRecord)
        .outerjoin(BotRuntimeRecord, BotRuntimeRecord.bot_instance_id == BotInstanceRecord.id)
        .where(
            BotInstanceRecord.is_active.is_(True),
            BotInstanceRecord.deleted_at.is_(None),
        )
        .order_by(BotInstanceRecord.order, BotInstanceRecord.id)
    ).all()
    return [
        BotProcessManifestItem(
            bot_instance_id=bot.id,
            slug=bot.slug,
            credential_env_key=(
                (runtime.credential_env_key if runtime is not None else None)
                or ("MAX_BOT_TOKEN" if bot.slug == settings.DEFAULT_BOT_SLUG else None)
            ),
            mode=runtime.mode if runtime is not None else "polling",
            runtime_token_configured=bool(runtime and runtime.runtime_token_hash),
        )
        for bot, runtime in rows
    ]


@router.post("/runtime/heartbeat", response_model=RuntimeResponse)
def heartbeat(
    payload: RuntimeHeartbeatRequest,
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    x_bot_runtime_token: str | None = Header(default=None, alias="X-Bot-Runtime-Token"),
    x_bot_token: str | None = Header(default=None, alias="X-Bot-Token"),
) -> RuntimeResponse:
    if bot.id is None:
        raise not_found("Бот не найден", code="bot_not_found")
    authorize_bot_runtime(db, bot.id, x_bot_runtime_token, x_bot_token)
    runtime = _get_or_create(db, bot.id)
    runtime.last_seen_at = datetime.now(tz=timezone.utc)
    if payload.username:
        runtime.username = payload.username
    if payload.user_id:
        runtime.max_bot_id = payload.user_id
    runtime.runtime_version = payload.version
    runtime.last_error_code = payload.error_code
    db.commit()
    db.refresh(runtime)
    return _response(runtime)
