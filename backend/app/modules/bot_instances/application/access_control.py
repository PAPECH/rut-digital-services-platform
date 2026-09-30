from __future__ import annotations

from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal
from ..infrastructure.staff_access_repository import SqlAlchemyStaffAccessRepository


def admin_has_bot_permission(
    db: Session,
    principal: CurrentPrincipal,
    bot_instance_id: int,
    *permission_flags: str,
) -> bool:
    """Single source of truth for "does this admin have permission on this bot" —
    every module used to re-implement this by querying AdminBotAccessRecord directly
    (Task 053 audit finding: the same check independently duplicated in 8+ modules'
    presentation/dependencies.py files, one missed update away from an authorization
    inconsistency between modules).

    True when `principal` is a platform admin (who always has cross-tenant access), or
    when they hold a bot-scoped access row for `bot_instance_id` whose StaffPermissions
    has at least one of `permission_flags` set. Passing no flags checks for *any* access
    row at all — the "does this admin have access to this bot, full stop" case
    (`require_tenant_access`'s admin branch).

    Lives in `application/`, not `presentation/`, specifically to avoid a package-init
    circular import: `bot_instances/presentation/__init__.py` eagerly imports its own
    router, and several modules' `presentation/dependencies.py` (including
    `tenancy/presentation/dependencies.py`, which `bot_instances/presentation/router.py`
    itself imports) need to call this — importing it from `bot_instances/presentation`
    would re-trigger that router import mid-load.
    """
    if principal.is_platform_admin:
        return True
    if principal.admin_id is None:
        return False
    access = SqlAlchemyStaffAccessRepository(db).get_by_staff(bot_instance_id, principal.admin_id)
    if access is None:
        return False
    if not permission_flags:
        return True
    return any(getattr(access.permissions, flag) for flag in permission_flags)
