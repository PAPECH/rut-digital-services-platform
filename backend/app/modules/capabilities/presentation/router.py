from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_platform_admin, require_student
from ....core.errors import conflict, not_found, service_unavailable, unprocessable
from ....db.session import get_db
from ....modules.audit.infrastructure.models import AuditLog
from ....modules.maintenance.presentation.dependencies import enforce_user_access_available
from ....services.log_action import ActionType, log_action
from ....services.rate_limit import rate_limit
from ...bot_instances.domain.entities import BotInstance
from ...tenancy.presentation.dependencies import require_tenant_access
from ..admission_rating.domain.config import (
    InvalidAdmissionRatingConfig,
    parse_admission_rating_config,
)
from ..admission_rating.infrastructure.provider import (
    RutAdmissionProvider,
    provider_error_code as admission_provider_error_code,
)
from ..application.commands import ConfigureCapabilityCommand, SetCapabilityEnabledCommand
from ..application.use_cases import (
    CapabilityConfigRevisionConflict,
    CapabilityConfigurationRequired,
    CapabilityDisabled,
    CapabilityNotInstalled,
    ConfigureCapability,
    ListCapabilityCatalog,
    ListCapabilityInstallations,
    ReorderCapabilityInstallations,
    SetCapabilityEnabled,
)
from ..domain.entities import CapabilityDescriptor, CapabilityInstallation, UnknownCapability
from ..infrastructure.catalog import capability_registry
from ..infrastructure.repositories import SqlAlchemyCapabilityInstallationRepository
from ..request_status.domain.config import InvalidRequestStatusConfig, parse_request_status_config
from ..request_status.infrastructure.provider import (
    GoogleSheetsStatusProvider,
    provider_error_code as request_status_provider_error_code,
)
from .dependencies import CapabilityManagerContext, require_capability_manager
from .schemas import (
    CapabilityConfigRequest,
    CapabilityDescriptorResponse,
    CapabilityInstallationResponse,
    CapabilityReorderRequest,
    CapabilityViewOpenRequest,
    CapabilityViewResponse,
)

router = APIRouter()
_test_limit = rate_limit("capability_config_test", limit=10, window_seconds=60)


def _bot_id(bot: BotInstance) -> int:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    return bot.id


def _view_response(capability_key: str, view) -> CapabilityViewResponse:
    return CapabilityViewResponse(
        key=view.key,
        title=view.title,
        subtitle=view.subtitle,
        icon=view.icon,
        path=f"/capabilities/{capability_key}/{view.key}",
        requires_complete_profile=view.requires_complete_profile,
    )


def _descriptor_response(descriptor: CapabilityDescriptor) -> CapabilityDescriptorResponse:
    return CapabilityDescriptorResponse(
        key=descriptor.key,
        version=descriptor.version,
        name=descriptor.name,
        description=descriptor.description,
        admin_editor_key=descriptor.admin_editor_key,
        views=[_view_response(descriptor.key, view) for view in descriptor.views],
    )


def _installation_response(
    installation: CapabilityInstallation,
    descriptor: CapabilityDescriptor,
) -> CapabilityInstallationResponse:
    return CapabilityInstallationResponse(
        id=installation.id,
        bot_instance_id=installation.bot_instance_id,
        capability_key=installation.capability_key,
        version=descriptor.version,
        name=descriptor.name,
        description=descriptor.description,
        admin_editor_key=descriptor.admin_editor_key,
        is_enabled=installation.is_enabled,
        order=installation.order,
        config=installation.config,
        config_revision=installation.config_revision,
        last_health_status=installation.last_health_status,
        last_health_at=installation.last_health_at,
        last_health_error_code=installation.last_health_error_code,
        views=[_view_response(descriptor.key, view) for view in descriptor.views],
    )


def _audit(
    db: Session,
    *,
    admin_id: int | None,
    installation: CapabilityInstallation,
    action: str,
    changed_fields: list[str] | None = None,
    result_code: str = "ok",
) -> None:
    db.add(
        AuditLog(
            admin_id=admin_id,
            bot_instance_id=installation.bot_instance_id,
            method="CAPABILITY",
            path=f"/api/capabilities/admin/{installation.capability_key}",
            status_code=200,
            meta={
                "action": action,
                "bot_instance_id": installation.bot_instance_id,
                "installation_id": installation.id,
                "capability_key": installation.capability_key,
                "config_revision": installation.config_revision,
                "changed_fields": changed_fields or [],
                "result_code": result_code,
            },
        )
    )


def _raise_capability_error(exc: Exception) -> None:
    if isinstance(exc, UnknownCapability | CapabilityNotInstalled):
        raise not_found(
            "Capability is not installed in this deployment", code="capability_not_installed"
        ) from exc
    if isinstance(exc, CapabilityDisabled):
        raise not_found("Capability is disabled", code="capability_disabled") from exc
    if isinstance(exc, CapabilityConfigRevisionConflict):
        raise conflict(
            "Capability configuration was changed by another administrator",
            code="capability_config_revision_conflict",
        ) from exc
    if isinstance(exc, CapabilityConfigurationRequired):
        raise conflict(
            "Configure the capability before enabling it",
            code="capability_configuration_required",
        ) from exc
    if isinstance(exc, InvalidRequestStatusConfig):
        raise unprocessable(
            str(exc),
            code="capability_config_invalid",
            path=exc.path,
        ) from exc
    if isinstance(exc, InvalidAdmissionRatingConfig):
        raise unprocessable(
            str(exc),
            code="capability_config_invalid",
            path=exc.path,
        ) from exc
    if isinstance(exc, ValueError):
        raise unprocessable(str(exc), code="capability_config_invalid") from exc
    raise exc


@router.get("/catalog", response_model=list[CapabilityDescriptorResponse])
def list_catalog(
    context: CapabilityManagerContext = Depends(require_capability_manager),
    db: Session = Depends(get_db),
) -> list[CapabilityDescriptorResponse]:
    descriptors = ListCapabilityCatalog(capability_registry).execute()
    if not context.principal.is_platform_admin:
        installed = {
            item.capability_key
            for item in ListCapabilityInstallations(SqlAlchemyCapabilityInstallationRepository(db)).execute(
                _bot_id(context.bot)
            )
            if item.is_enabled
        }
        descriptors = tuple(item for item in descriptors if item.key in installed)
    return [_descriptor_response(item) for item in descriptors]


@router.get("/admin", response_model=list[CapabilityInstallationResponse])
def list_installations(
    context: CapabilityManagerContext = Depends(require_capability_manager),
    db: Session = Depends(get_db),
) -> list[CapabilityInstallationResponse]:
    repository = SqlAlchemyCapabilityInstallationRepository(db)
    installations = ListCapabilityInstallations(repository).execute(_bot_id(context.bot))
    if context.principal.is_platform_admin:
        by_key = {item.capability_key: item for item in installations}
        for descriptor in capability_registry.list():
            if descriptor.key not in by_key:
                by_key[descriptor.key] = CapabilityInstallation(
                    id=None,
                    bot_instance_id=_bot_id(context.bot),
                    capability_key=descriptor.key,
                )
        installations = list(by_key.values())
    return [
        _installation_response(item, capability_registry.get(item.capability_key))
        for item in installations
        if context.principal.is_platform_admin or item.is_enabled
    ]


@router.post("/admin/reorder", response_model=list[CapabilityInstallationResponse])
def reorder_installations(
    payload: CapabilityReorderRequest,
    bot: BotInstance = Depends(require_tenant_access),
    principal: CurrentPrincipal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[CapabilityInstallationResponse]:
    repository = SqlAlchemyCapabilityInstallationRepository(db)
    try:
        installations = ReorderCapabilityInstallations(repository).execute(
            _bot_id(bot), payload.capability_keys
        )
        for installation in installations:
            _audit(
                db,
                admin_id=principal.admin_id,
                installation=installation,
                action="capabilities_reordered",
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_capability_error(exc)
    return [
        _installation_response(item, capability_registry.get(item.capability_key)) for item in installations
    ]


@router.put("/admin/{capability_key}/config", response_model=CapabilityInstallationResponse)
def configure_capability(
    capability_key: str,
    payload: CapabilityConfigRequest,
    context: CapabilityManagerContext = Depends(require_capability_manager),
    db: Session = Depends(get_db),
) -> CapabilityInstallationResponse:
    repository = SqlAlchemyCapabilityInstallationRepository(db)
    try:
        installation = ConfigureCapability(repository, capability_registry).execute(
            ConfigureCapabilityCommand(
                bot_instance_id=_bot_id(context.bot),
                capability_key=capability_key,
                config=payload.config,
                expected_revision=payload.expected_revision,
                configured_by=context.principal.admin_id,
                create_if_missing=context.principal.is_platform_admin,
                require_enabled=not context.principal.is_platform_admin,
            )
        )
        _audit(
            db,
            admin_id=context.principal.admin_id,
            installation=installation,
            action="capability_configured",
            changed_fields=sorted(payload.config),
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_capability_error(exc)
    return _installation_response(installation, capability_registry.get(capability_key))


def _set_enabled(
    *,
    capability_key: str,
    enabled: bool,
    bot: BotInstance,
    principal: CurrentPrincipal,
    db: Session,
) -> CapabilityInstallationResponse:
    repository = SqlAlchemyCapabilityInstallationRepository(db)
    try:
        installation = SetCapabilityEnabled(repository, capability_registry).execute(
            SetCapabilityEnabledCommand(
                bot_instance_id=_bot_id(bot),
                capability_key=capability_key,
                enabled=enabled,
                changed_by=principal.admin_id,
            )
        )
        _audit(
            db,
            admin_id=principal.admin_id,
            installation=installation,
            action="capability_enabled" if enabled else "capability_disabled",
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_capability_error(exc)
    return _installation_response(installation, capability_registry.get(capability_key))


def _reject_if_capability_needs_profile_but_it_is_disabled(bot: BotInstance, capability_key: str) -> None:
    """Task 054: a bot with profile.enabled=false cannot enable a capability that has a
    view requiring a complete profile — the symmetric half of bot_instances' own
    profile-disable check (which rejects disabling profile while such a capability is
    already enabled)."""
    profile_enabled = (bot.settings.get("profile") or {}).get("enabled", True)
    if profile_enabled:
        return
    try:
        descriptor = capability_registry.get(capability_key)
    except UnknownCapability:
        return  # an unknown key is reported downstream by the normal enable flow
    if any(view.requires_complete_profile for view in descriptor.views):
        raise conflict(
            "Нельзя включить эту capability: ей нужен заполненный профиль, а вкладка "
            "«Профиль» у этого бота отключена — сначала включите её в настройках бота",
            code="capability_requires_profile_enabled",
        )


@router.post("/admin/{capability_key}/enable", response_model=CapabilityInstallationResponse)
def enable_capability(
    capability_key: str,
    bot: BotInstance = Depends(require_tenant_access),
    principal: CurrentPrincipal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> CapabilityInstallationResponse:
    _reject_if_capability_needs_profile_but_it_is_disabled(bot, capability_key)
    return _set_enabled(
        capability_key=capability_key,
        enabled=True,
        bot=bot,
        principal=principal,
        db=db,
    )


@router.post("/admin/{capability_key}/disable", response_model=CapabilityInstallationResponse)
def disable_capability(
    capability_key: str,
    bot: BotInstance = Depends(require_tenant_access),
    principal: CurrentPrincipal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> CapabilityInstallationResponse:
    return _set_enabled(
        capability_key=capability_key,
        enabled=False,
        bot=bot,
        principal=principal,
        db=db,
    )


@router.post(
    "/admin/{capability_key}/test",
    response_model=CapabilityInstallationResponse,
    dependencies=[Depends(_test_limit)],
)
async def test_capability(
    capability_key: str,
    context: CapabilityManagerContext = Depends(require_capability_manager),
    db: Session = Depends(get_db),
) -> CapabilityInstallationResponse:
    repository = SqlAlchemyCapabilityInstallationRepository(db)
    installation = repository.get(_bot_id(context.bot), capability_key)
    if installation is None:
        raise not_found("Capability is not installed for this bot", code="capability_not_installed")
    if not context.principal.is_platform_admin and not installation.is_enabled:
        raise not_found("Capability is disabled", code="capability_disabled")
    try:
        if capability_key == "request_status":
            config = parse_request_status_config(installation.config)
            GoogleSheetsStatusProvider(circuit_key=f"{_bot_id(context.bot)}:{installation.id}").read_statuses(
                config
            )
        elif capability_key == "admission_rating":
            await RutAdmissionProvider().probe(parse_admission_rating_config(installation.config))
        else:
            raise UnknownCapability(capability_key)
        installation = repository.save(
            replace(
                installation,
                last_health_status="healthy",
                last_health_at=datetime.now(tz=UTC),
                last_health_error_code=None,
            )
        )
        _audit(
            db,
            admin_id=context.principal.admin_id,
            installation=installation,
            action="capability_tested",
        )
        db.commit()
    except (
        InvalidAdmissionRatingConfig,
        InvalidRequestStatusConfig,
        UnknownCapability,
    ) as exc:
        db.rollback()
        _raise_capability_error(exc)
    except Exception as exc:
        db.rollback()
        installation = repository.get(_bot_id(context.bot), capability_key)
        assert installation is not None
        installation = repository.save(
            replace(
                installation,
                last_health_status="degraded",
                last_health_at=datetime.now(tz=UTC),
                last_health_error_code=(
                    request_status_provider_error_code(exc)
                    if capability_key == "request_status"
                    else admission_provider_error_code(exc)
                ),
            )
        )
        _audit(
            db,
            admin_id=context.principal.admin_id,
            installation=installation,
            action="capability_tested",
            result_code="provider_unavailable",
        )
        db.commit()
        raise service_unavailable(
            "Capability provider is unavailable",
            code="capability_provider_unavailable",
        ) from exc
    return _installation_response(installation, capability_registry.get(capability_key))


@router.post(
    "/{capability_key}/events/view-open",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(enforce_user_access_available)],
)
def record_capability_view_open(
    capability_key: str,
    payload: CapabilityViewOpenRequest,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> Response:
    installation = SqlAlchemyCapabilityInstallationRepository(db).get(_bot_id(bot), capability_key)
    if installation is None or installation.id != payload.installation_id or not installation.is_enabled:
        raise not_found("Capability is unavailable", code="capability_disabled")
    try:
        descriptor = capability_registry.get(capability_key)
        descriptor.get_view(payload.view_key)
        descriptor.validate_config(installation.config)
    except (LookupError, ValueError) as exc:
        raise not_found("Capability view is unavailable", code="capability_disabled") from exc
    log_action(
        db,
        bot_instance_id=_bot_id(bot),
        user_id=principal.user_id,
        action_type=ActionType.CAPABILITY_VIEW_OPEN,
        capability_installation_id=installation.id,
        capability_key=capability_key,
        capability_view_key=payload.view_key,
        commit=True,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
