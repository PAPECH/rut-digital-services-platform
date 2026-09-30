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
class FormManagerContext:
    bot: BotInstance
    principal: CurrentPrincipal


def require_form_manager(
    bot: BotInstance = Depends(require_tenant_access),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> FormManagerContext:
    if not admin_has_bot_permission(db, principal, bot.id, "can_manage_forms"):
        raise forbidden("No permission to manage forms", code="form_access_denied")
    return FormManagerContext(bot=bot, principal=principal)


def require_form_reader(
    bot: BotInstance = Depends(require_tenant_access),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> FormManagerContext:
    """Allow form managers and submission processors to read the form catalog."""
    if not admin_has_bot_permission(
        db, principal, bot.id, "can_manage_forms", "can_process_submissions"
    ):
        raise forbidden("No permission to read forms", code="form_access_denied")
    return FormManagerContext(bot=bot, principal=principal)
