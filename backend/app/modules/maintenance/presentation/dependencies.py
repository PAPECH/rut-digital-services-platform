from fastapi import Depends
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal
from ....core.errors import service_unavailable
from ....db.session import get_db
from ...bot_instances.domain.entities import BotInstance
from ...tenancy.presentation.dependencies import require_tenant_access
from ..application.services import GetEffectiveMaintenance
from ..infrastructure.repositories import SqlAlchemyMaintenanceRepository


def enforce_user_write_available(
    bot: BotInstance = Depends(require_tenant_access),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> None:
    if principal.role != "student" or bot.id is None:
        return
    policy = GetEffectiveMaintenance(SqlAlchemyMaintenanceRepository(db)).execute(bot.id)
    if policy and policy.blocks_user_writes:
        raise service_unavailable(
            policy.message or "Ведутся технические работы",
            code="maintenance_mode",
            retry_after=policy.retry_after_seconds,
            mode=policy.mode.value,
        )


def enforce_user_access_available(
    bot: BotInstance = Depends(require_tenant_access),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> None:
    if principal.role != "student" or bot.id is None:
        return
    policy = GetEffectiveMaintenance(SqlAlchemyMaintenanceRepository(db)).execute(bot.id)
    if policy and policy.blocks_user_access:
        raise service_unavailable(
            policy.message or "Ведутся технические работы",
            code="maintenance_mode",
            retry_after=policy.retry_after_seconds,
            mode=policy.mode.value,
        )
