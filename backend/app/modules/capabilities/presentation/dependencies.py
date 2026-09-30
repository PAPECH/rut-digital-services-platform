from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal
from ....core.errors import forbidden
from ....db.session import get_db
from ...bot_instances.domain.entities import BotInstance
from ...bot_instances.application.access_control import admin_has_bot_permission
from ...tenancy.presentation.dependencies import require_tenant_access


@dataclass(frozen=True, slots=True)
class CapabilityManagerContext:
    bot: BotInstance
    principal: CurrentPrincipal


def require_capability_manager(
    bot: BotInstance = Depends(require_tenant_access),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> CapabilityManagerContext:
    if not admin_has_bot_permission(db, principal, bot.id, "can_manage_capabilities"):
        raise forbidden(
            "No permission to manage capabilities",
            code="capability_access_denied",
        )
    return CapabilityManagerContext(bot=bot, principal=principal)
