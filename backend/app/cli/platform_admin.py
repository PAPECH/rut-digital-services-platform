from __future__ import annotations

import argparse

from ..db.model_registry import load_all_models
from ..db.session import SessionLocal
from ..modules.audit.infrastructure.models import AuditLog
from ..modules.platform_admins.application.commands import EnsurePlatformAdminCommand
from ..modules.platform_admins.application.use_cases import EnsurePlatformAdmin
from ..modules.platform_admins.infrastructure.repository import (
    SqlAlchemyPlatformAdminRepository,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create, promote, or reactivate a platform administrator",
    )
    parser.add_argument("--max-user-id", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()
    load_all_models()

    with SessionLocal() as db:
        try:
            result = EnsurePlatformAdmin(SqlAlchemyPlatformAdminRepository(db)).execute(
                EnsurePlatformAdminCommand(
                    max_user_id=args.max_user_id,
                    full_name=args.full_name,
                )
            )
            if result.identity.id is None:
                raise RuntimeError("Platform administrator was not persisted")
            db.add(
                AuditLog(
                    admin_id=None,
                    bot_instance_id=None,
                    method="CLI",
                    path="platform-admin:ensure",
                    status_code=201 if result.created else 200,
                    meta={
                        "action": "platform_admin_bootstrapped",
                        "target_admin_id": result.identity.id,
                        "created": result.created,
                        "promoted": result.previous_role not in {None, "platform_admin"},
                        "reactivated": result.reactivated,
                        "previous_role": result.previous_role,
                    },
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    action = "created" if result.created else "updated"
    print(f"Platform administrator #{result.identity.id} {action} successfully")


if __name__ == "__main__":
    main()
