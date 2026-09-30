from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_admin
from ....core.errors import not_found
from ....db.session import get_db
from ...tenancy.presentation.dependencies import require_tenant_access, resolve_tenant
from ..domain.entities import BotInstance
from ..infrastructure.settings_repository import SqlAlchemySettingRepository
from .dependencies import authorize_setting_read
from .settings_schemas import SettingIn, SettingOut

router = APIRouter()


@router.get("/{key}", response_model=SettingOut)
def get_setting(
    key: str,
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    x_bot_token: str | None = Header(default=None, alias="X-Bot-Token"),
    x_bot_runtime_token: str | None = Header(default=None, alias="X-Bot-Runtime-Token"),
    authorization: str | None = Header(default=None),
) -> SettingOut:
    if bot.id is None:
        raise not_found("Бот не найден", code="bot_not_found")
    authorize_setting_read(x_bot_token, x_bot_runtime_token, authorization, bot.id, db)
    setting = SqlAlchemySettingRepository(db).get(bot.id, key)
    # Отдаём 200 c value=null, чтобы бот мог гладко использовать дефолт
    return SettingOut(key=key, value=setting.value if setting else None)


@router.get("", response_model=list[SettingOut])
def list_settings(
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[SettingOut]:
    items = SqlAlchemySettingRepository(db).list_for_bot(bot.id)
    return [SettingOut(key=i.key, value=i.value) for i in items]


@router.put("/{key}", response_model=SettingOut)
def put_setting(
    key: str,
    payload: SettingIn,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
) -> SettingOut:
    setting = SqlAlchemySettingRepository(db).upsert(bot.id, key, payload.value)
    return SettingOut(key=setting.key, value=setting.value)


@router.delete("/{key}", status_code=204)
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
):
    deleted = SqlAlchemySettingRepository(db).delete(bot.id, key)
    if not deleted:
        raise not_found("Настройка не найдена")
