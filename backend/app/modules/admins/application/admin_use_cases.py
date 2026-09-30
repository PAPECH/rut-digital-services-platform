from __future__ import annotations

from ..domain.admin_account import AdminAccount, AdminRole
from ..domain.admin_repository import AdminAccountRepository


class AdminAccountAlreadyExists(RuntimeError):
    pass


class AdminAccountNotFound(RuntimeError):
    pass


class CannotModifyOwnPrivileges(RuntimeError):
    pass


class CreateAdminAccount:
    def __init__(self, repository: AdminAccountRepository) -> None:
        self._repository = repository

    def execute(
        self, *, max_user_id: str, full_name: str, role: AdminRole, is_active: bool
    ) -> AdminAccount:
        if self._repository.find_by_max_user_id(max_user_id) is not None:
            raise AdminAccountAlreadyExists(max_user_id)
        return self._repository.add(
            AdminAccount(
                id=None,
                max_user_id=max_user_id,
                full_name=full_name,
                role=role,
                is_active=is_active,
            )
        )


class UpdateAdminAccount:
    def __init__(self, repository: AdminAccountRepository) -> None:
        self._repository = repository

    def execute(
        self, admin_id: int, changes: dict[str, object], *, actor_admin_id: int | None
    ) -> AdminAccount:
        account = self._repository.get(admin_id)
        if account is None:
            raise AdminAccountNotFound(admin_id)

        # Защита: нельзя самого себя деактивировать или понизить — иначе можно остаться без админов
        if account.id == actor_admin_id:
            if changes.get("is_active") is False:
                raise CannotModifyOwnPrivileges("Нельзя деактивировать самого себя")
            new_role = changes.get("role")
            if new_role is not None and new_role != account.role:
                raise CannotModifyOwnPrivileges("Нельзя понизить самого себя")

        return self._repository.update(admin_id, changes)


class DeleteAdminAccount:
    def __init__(self, repository: AdminAccountRepository) -> None:
        self._repository = repository

    def execute(self, admin_id: int, *, actor_admin_id: int | None) -> None:
        account = self._repository.get(admin_id)
        if account is None:
            raise AdminAccountNotFound(admin_id)
        if account.id == actor_admin_id:
            raise CannotModifyOwnPrivileges("Нельзя удалить самого себя")
        self._repository.delete(admin_id)
