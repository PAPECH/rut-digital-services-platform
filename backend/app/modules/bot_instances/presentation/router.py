from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal, require_platform_admin
from ....core.config import settings
from ....core.errors import bad_request, conflict, forbidden, not_found
from ....db.session import get_db
from ...audit.infrastructure.models import AuditLog
from ...tenancy.presentation.dependencies import require_tenant_access
from ...capabilities.application.use_cases import bot_has_profile_gated_capability
from ...capabilities.infrastructure.catalog import capability_registry
from ...capabilities.infrastructure.repositories import SqlAlchemyCapabilityInstallationRepository
from ..application.access_control import admin_has_bot_permission
from ..application.commands import CreateBotInstanceCommand, UpdateBotInstanceCommand
from ..application.provisioning import ProvisionBotInstance, ProvisionBotInstanceCommand
from ..application.use_cases import (
    BotInstanceNotFound,
    BotSlugAlreadyExists,
    DeleteBotInstance,
    ListBotInstances,
    ProfileDisabledWithGatedCapability,
    ProfileDisabledWithRequiredFields,
    RestoreBotInstance,
    UpdateBotInstance,
)
from ..domain.entities import BotInstance
from ..domain.runtime_credentials import InvalidBotCredential
from ..infrastructure.env_file_credentials import EnvFileRuntimeCredentialStore
from ..infrastructure.models import AdminBotAccessRecord, BotInstanceRecord
from ..infrastructure.repositories import SqlAlchemyBotInstanceRepository
from ..infrastructure.runtime_repository import SqlAlchemyBotRuntimeBinder
from .schemas import BotInstanceCreateRequest, BotInstancePatchRequest, BotInstanceResponse, BotSettings

router = APIRouter()

_PROFILE_REQUIRED_FIELDS_MESSAGE = (
    "Нельзя отключить вкладку «Профиль»: в анкете есть обязательные поля — "
    "сначала снимите отметку «обязательное» с них"
)
_PROFILE_GATED_CAPABILITY_MESSAGE = (
    "Нельзя отключить вкладку «Профиль»: включена capability, для которой нужен заполненный "
    "профиль — сначала отключите её"
)


def _update_bot_instance(repository: SqlAlchemyBotInstanceRepository, db: Session) -> UpdateBotInstance:
    return UpdateBotInstance(
        repository,
        has_profile_gated_capability=lambda bot_id: bot_has_profile_gated_capability(
            SqlAlchemyCapabilityInstallationRepository(db), capability_registry, bot_id
        ),
    )


def _response(bot: BotInstance) -> BotInstanceResponse:
    return (
        BotInstanceResponse(**bot.__dict__)
        if hasattr(bot, "__dict__")
        else BotInstanceResponse(
            id=bot.id or 0,
            slug=bot.slug,
            name=bot.name,
            description=bot.description,
            is_active=bot.is_active,
            order=bot.order,
            branding=bot.branding,
            settings=bot.settings,
            profile_schema=bot.profile_schema,
            deleted_at=bot.deleted_at,
        )
    )


@router.get("/current", response_model=BotInstanceResponse)
def get_current_instance(bot: BotInstance = Depends(require_tenant_access)) -> BotInstanceResponse:
    return _response(bot)


@router.patch("/current/settings", response_model=BotInstanceResponse)
def patch_current_instance_settings(
    payload: BotSettings,
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> BotInstanceResponse:
    if bot.id is None:
        raise not_found("Bot instance not found")
    if not admin_has_bot_permission(db, principal, bot.id, "can_manage_content"):
        raise forbidden(
            "No permission to manage bot interface settings",
            code="bot_settings_access_denied",
        )
    try:
        updated = _update_bot_instance(SqlAlchemyBotInstanceRepository(db), db).execute(
            UpdateBotInstanceCommand(
                bot_id=bot.id,
                settings=payload.model_dump(mode="json"),
            )
        )
    except ProfileDisabledWithRequiredFields as exc:
        raise conflict(
            _PROFILE_REQUIRED_FIELDS_MESSAGE, code="profile_disabled_with_required_fields"
        ) from exc
    except ProfileDisabledWithGatedCapability as exc:
        raise conflict(
            _PROFILE_GATED_CAPABILITY_MESSAGE, code="profile_disabled_with_gated_capability"
        ) from exc
    db.add(
        AuditLog(
            admin_id=principal.admin_id,
            bot_instance_id=bot.id,
            method="PATCH",
            path="/api/bot-instances/current/settings",
            status_code=200,
            meta={"action": "bot_interface_settings_updated"},
        )
    )
    db.commit()
    return _response(updated)


@router.get("", response_model=list[BotInstanceResponse])
def list_instances(
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> list[BotInstanceResponse]:
    repository = SqlAlchemyBotInstanceRepository(db)
    if principal.is_platform_admin:
        bots = ListBotInstances(repository).execute(include_deleted=include_deleted)
    elif principal.is_staff and principal.admin_id:
        records = db.execute(
            select(BotInstanceRecord)
            .join(AdminBotAccessRecord)
            .where(
                AdminBotAccessRecord.admin_id == principal.admin_id,
                BotInstanceRecord.deleted_at.is_(None),
            )
            .order_by(BotInstanceRecord.order, BotInstanceRecord.id)
        ).scalars()
        bots = [repository.get(record.id) for record in records]
        bots = [bot for bot in bots if bot is not None]
    else:
        bots = []
    return [_response(bot) for bot in bots]


@router.post("", response_model=BotInstanceResponse, status_code=201)
def create_instance(
    payload: BotInstanceCreateRequest,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_platform_admin),
) -> BotInstanceResponse:
    use_case = ProvisionBotInstance(
        bot_repository=SqlAlchemyBotInstanceRepository(db),
        credential_store=EnvFileRuntimeCredentialStore(settings.BOT_MANAGED_ENV_FILE),
        runtime_binder=SqlAlchemyBotRuntimeBinder(db),
    )
    create_fields = payload.model_dump(mode="json", exclude={"bot_token"})
    try:
        bot = use_case.execute(
            ProvisionBotInstanceCommand(
                create=CreateBotInstanceCommand(**create_fields),
                bot_token=payload.bot_token.get_secret_value(),
            )
        )
    except BotSlugAlreadyExists as exc:
        raise conflict("Bot slug already exists", code="bot_slug_exists") from exc
    except InvalidBotCredential as exc:
        raise bad_request(str(exc), code="invalid_bot_credential") from exc
    except ProfileDisabledWithRequiredFields as exc:
        raise conflict(
            _PROFILE_REQUIRED_FIELDS_MESSAGE, code="profile_disabled_with_required_fields"
        ) from exc
    db.add(
        AuditLog(
            admin_id=principal.admin_id,
            bot_instance_id=bot.id,
            method="POST",
            path="/api/bot-instances",
            status_code=201,
            meta={"action": "bot_instance_created"},
        )
    )
    db.commit()
    return _response(bot)


@router.delete("/{bot_id}", response_model=BotInstanceResponse)
def delete_instance(
    bot_id: int,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_platform_admin),
) -> BotInstanceResponse:
    use_case = DeleteBotInstance(SqlAlchemyBotInstanceRepository(db))
    try:
        bot = use_case.execute(bot_id)
    except BotInstanceNotFound as exc:
        raise not_found("Bot instance not found") from exc
    db.add(
        AuditLog(
            admin_id=principal.admin_id,
            bot_instance_id=bot_id,
            method="DELETE",
            path=f"/api/bot-instances/{bot_id}",
            status_code=200,
            meta={"action": "bot_instance_deleted"},
        )
    )
    db.commit()
    return _response(bot)


@router.post("/{bot_id}/restore", response_model=BotInstanceResponse)
def restore_instance(
    bot_id: int,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_platform_admin),
) -> BotInstanceResponse:
    use_case = RestoreBotInstance(SqlAlchemyBotInstanceRepository(db))
    try:
        bot = use_case.execute(bot_id)
    except BotInstanceNotFound as exc:
        raise not_found("Bot instance not found") from exc
    except (BotSlugAlreadyExists, IntegrityError) as exc:
        # IntegrityError covers the race the pre-check can't fully close: two concurrent restores
        # for bots sharing a slug can both pass get_by_slug before either commits, so the DB's
        # partial unique index (uq_bot_instances_slug_live) is the actual last line of defense.
        db.rollback()
        raise conflict(
            "A live bot already uses this slug; rename it before restoring",
            code="bot_slug_exists",
        ) from exc
    db.add(
        AuditLog(
            admin_id=principal.admin_id,
            bot_instance_id=bot_id,
            method="POST",
            path=f"/api/bot-instances/{bot_id}/restore",
            status_code=200,
            meta={"action": "bot_instance_restored"},
        )
    )
    db.commit()
    return _response(bot)


@router.patch("/{bot_id}", response_model=BotInstanceResponse)
def patch_instance(
    bot_id: int,
    payload: BotInstancePatchRequest,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> BotInstanceResponse:
    use_case = _update_bot_instance(SqlAlchemyBotInstanceRepository(db), db)
    try:
        bot = use_case.execute(
            UpdateBotInstanceCommand(bot_id=bot_id, **payload.model_dump(exclude_unset=True, mode="json"))
        )
    except BotInstanceNotFound as exc:
        raise not_found("Bot instance not found") from exc
    except ProfileDisabledWithRequiredFields as exc:
        raise conflict(
            _PROFILE_REQUIRED_FIELDS_MESSAGE, code="profile_disabled_with_required_fields"
        ) from exc
    except ProfileDisabledWithGatedCapability as exc:
        raise conflict(
            _PROFILE_GATED_CAPABILITY_MESSAGE, code="profile_disabled_with_gated_capability"
        ) from exc
    db.commit()
    return _response(bot)
