from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal, require_platform_admin
from ....core.errors import bad_request, forbidden
from ....db.session import get_db
from ...bot_instances.domain.entities import BotInstance
from ...bot_instances.application.access_control import admin_has_bot_permission
from ...capabilities.infrastructure.catalog import capability_registry
from ...capabilities.infrastructure.repositories import (
    SqlAlchemyCapabilityInstallationRepository,
)
from ...capabilities.presentation.schemas import (
    CapabilityViewResponse,
    PublicCapabilityResponse,
)
from ...tenancy.presentation.dependencies import require_tenant_access, resolve_tenant
from ..application.commands import SetMaintenanceCommand
from ..application.services import GetEffectiveMaintenance, SetMaintenance
from ..domain.policies import MaintenancePolicy
from ..infrastructure.repositories import SqlAlchemyMaintenanceRepository
from .schemas import (
    AppManifestResponse,
    MaintenancePatchRequest,
    MaintenanceResponse,
    ManifestBot,
)

router = APIRouter()


def _off_policy(scope_key: str, bot_instance_id: int | None) -> MaintenancePolicy:
    return MaintenancePolicy(scope_key=scope_key, bot_instance_id=bot_instance_id)


@router.get("/manifest", response_model=AppManifestResponse)
def get_manifest(
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
) -> AppManifestResponse:
    assert bot.id is not None
    policy = GetEffectiveMaintenance(SqlAlchemyMaintenanceRepository(db)).execute(bot.id)
    capabilities: list[PublicCapabilityResponse] = []
    for installation in SqlAlchemyCapabilityInstallationRepository(db).list_for_bot(bot.id):
        if not installation.is_enabled or installation.id is None:
            continue
        try:
            descriptor = capability_registry.get(installation.capability_key)
            public_config = descriptor.public_config(installation.config)
        except (LookupError, ValueError):
            continue
        capabilities.append(
            PublicCapabilityResponse(
                installation_id=installation.id,
                key=descriptor.key,
                version=descriptor.version,
                views=[
                    CapabilityViewResponse(
                        key=view.key,
                        title=view.title,
                        subtitle=view.subtitle,
                        icon=view.icon,
                        path=f"/capabilities/{descriptor.key}/{view.key}",
                        requires_complete_profile=view.requires_complete_profile,
                    )
                    for view in descriptor.views
                ],
                public_config=public_config,
            )
        )
    return AppManifestResponse(
        bot=ManifestBot(
            id=bot.id,
            slug=bot.slug,
            name=bot.name,
            description=bot.description,
            branding=bot.branding,
            settings=bot.settings,
            profile_schema=bot.profile_schema,
        ),
        maintenance=MaintenanceResponse.from_domain(policy) if policy else None,
        capabilities=capabilities,
    )


@router.get("/maintenance/current", response_model=MaintenanceResponse)
def get_current_maintenance(
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> MaintenanceResponse:
    assert bot.id is not None
    repository = SqlAlchemyMaintenanceRepository(db)
    policy = repository.get(f"bot:{bot.id}") or _off_policy(f"bot:{bot.id}", bot.id)
    return MaintenanceResponse.from_domain(policy)


@router.patch("/maintenance/current", response_model=MaintenanceResponse)
def patch_current_maintenance(
    payload: MaintenancePatchRequest,
    bot: BotInstance = Depends(require_tenant_access),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MaintenanceResponse:
    assert bot.id is not None
    if not admin_has_bot_permission(db, principal, bot.id, "can_manage_maintenance"):
        raise forbidden("No permission to manage maintenance")
    command = SetMaintenanceCommand(
        scope_key=f"bot:{bot.id}",
        bot_instance_id=bot.id,
        updated_by=principal.admin_id,
        **payload.model_dump(),
    )
    try:
        policy = SetMaintenance(SqlAlchemyMaintenanceRepository(db)).execute(command)
    except ValueError as exc:
        raise bad_request(str(exc), code="invalid_maintenance_window") from exc
    db.commit()
    return MaintenanceResponse.from_domain(policy)


@router.get("/maintenance/global", response_model=MaintenanceResponse)
def get_global_maintenance(
    _: CurrentPrincipal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> MaintenanceResponse:
    repository = SqlAlchemyMaintenanceRepository(db)
    return MaintenanceResponse.from_domain(repository.get("global") or _off_policy("global", None))


@router.patch("/maintenance/global", response_model=MaintenanceResponse)
def patch_global_maintenance(
    payload: MaintenancePatchRequest,
    principal: CurrentPrincipal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> MaintenanceResponse:
    command = SetMaintenanceCommand(
        scope_key="global",
        bot_instance_id=None,
        updated_by=principal.admin_id,
        **payload.model_dump(),
    )
    try:
        policy = SetMaintenance(SqlAlchemyMaintenanceRepository(db)).execute(command)
    except ValueError as exc:
        raise bad_request(str(exc), code="invalid_maintenance_window") from exc
    db.commit()
    return MaintenanceResponse.from_domain(policy)
