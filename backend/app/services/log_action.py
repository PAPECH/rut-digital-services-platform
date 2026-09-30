from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from ..models.logger import UserAction
from ..modules.analytics.domain.events import AnalyticsEventName

ActionType = AnalyticsEventName


def log_action(
    session: Session,
    *,
    bot_instance_id: int,
    user_id: int,
    action_type: ActionType,
    description: str | None = None,
    payload: dict[str, Any] | None = None,
    event_id: str | None = None,
    session_id: str | None = None,
    source_surface: str | None = None,
    interaction_kind: str | None = None,
    category_id: int | None = None,
    source_category_id: int | None = None,
    content_version_id: int | None = None,
    block_id: str | None = None,
    item_id: str | None = None,
    tabs_block_id: str | None = None,
    tab_key: str | None = None,
    form_template_id: int | None = None,
    form_version_id: int | None = None,
    faq_id: int | None = None,
    news_id: int | None = None,
    attachment_id: int | None = None,
    capability_installation_id: int | None = None,
    capability_key: str | None = None,
    capability_view_key: str | None = None,
    outcome_code: str | None = None,
    commit: bool = False,
) -> UserAction:
    """
    Логирование действия пользователя.

    Args:
        session: SQLAlchemy Session
        user_id: внутренний ID пользователя (users.id)
        action_type: тип действия
        description: описание
        payload: дополнительные данные
        commit: выполнить commit после записи
    """

    action = UserAction(
        event_id=event_id or str(uuid4()),
        session_id=session_id,
        bot_instance_id=bot_instance_id,
        user_id=user_id,
        action_type=action_type.value,
        source_surface=source_surface,
        interaction_kind=interaction_kind,
        category_id=category_id,
        source_category_id=source_category_id,
        content_version_id=content_version_id,
        block_id=block_id,
        item_id=item_id,
        tabs_block_id=tabs_block_id,
        tab_key=tab_key,
        form_template_id=form_template_id,
        form_version_id=form_version_id,
        faq_id=faq_id,
        news_id=news_id,
        attachment_id=attachment_id,
        capability_installation_id=capability_installation_id,
        capability_key=capability_key,
        capability_view_key=capability_view_key,
        outcome_code=outcome_code,
        description=description,
        payload=payload,
    )

    session.add(action)

    if commit:
        session.commit()
        session.refresh(action)

    return action
