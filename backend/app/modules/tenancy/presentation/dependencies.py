from fastapi import Depends, Header
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal
from ....core.errors import bad_request, forbidden, not_found
from ....db.session import get_db
from ...bot_instances.domain.entities import BotInstance
from ...bot_instances.infrastructure.repositories import SqlAlchemyBotInstanceRepository
from ...bot_instances.application.access_control import admin_has_bot_permission


def resolve_tenant(
    x_bot_slug: str | None = Header(default=None, alias="X-Bot-Slug"),
    db: Session = Depends(get_db),
) -> BotInstance:
    # No implicit default: a request that doesn't name a bot is a caller bug, not a signal to
    # guess -- silently defaulting here would risk serving/writing another tenant's data (Task 035).
    slug = (x_bot_slug or "").strip().lower()
    if not slug:
        raise bad_request("X-Bot-Slug header is required", code="bot_slug_required")
    bot = SqlAlchemyBotInstanceRepository(db).get_by_slug(slug)
    if bot is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    if not bot.is_active:
        raise forbidden("Bot instance is disabled", code="bot_disabled")
    return bot


def require_tenant_access(
    bot: BotInstance = Depends(resolve_tenant),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> BotInstance:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    if principal.role == "student":
        if principal.bot_instance_id != bot.id:
            raise forbidden("Token belongs to another bot", code="tenant_mismatch")
        return bot
    if not admin_has_bot_permission(db, principal, bot.id):
        raise forbidden("No bot access", code="tenant_access_denied")
    return bot
