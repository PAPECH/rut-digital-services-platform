"""PUSH-уведомления студентам через бота MAX (§9.3, §14 ТЗ).

Transactional outbox: каждый вызов enqueue_push добавляет строку в push_outbox
в той же сессии, что и бизнес-операция. После фиксации транзакции воркер
доставляет запись в Redis с exponential backoff.

Это даёт два свойства:
 1) Если бизнес-транзакция откатилась — push не уйдёт (строка тоже откатится).
 2) Если Redis недоступен — push не теряется, воркер дошлёт.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.redis import redis_client
from ..models.push_outbox import PushOutbox
from ..modules.bot_instances.infrastructure.models import BotInstanceRecord
from ..modules.profiles.infrastructure.models import User

log = logging.getLogger(__name__)

PUSH_QUEUE_SUFFIX = ":push:queue"

# Параметры ретраев — экспоненциальный backoff с потолком.
_INITIAL_RETRY = timedelta(seconds=10)
_MAX_RETRY = timedelta(minutes=10)
_MAX_ATTEMPTS = 30


def _redis_item(*, user: User, bot_slug: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": kind,
        "user_pk": user.id,
        "external_user_id": user.user_id,
        "system": user.system.value,
        "bot_slug": bot_slug,
        "language_code": user.language_code or "ru",
        "payload": payload,
        "created_at": datetime.now(tz=UTC).isoformat(),
    }


def _push_to_redis(item: dict[str, Any]) -> None:
    queue = f"{item.get('system', 'max')}:{item['bot_slug']}" f"{PUSH_QUEUE_SUFFIX}"
    redis_client.rpush(queue, json.dumps(item, ensure_ascii=False))


def enqueue_push(
    db: Session,
    *,
    bot_instance_id: int,
    user_id: int,
    kind: str,
    payload: dict[str, Any],
) -> None:
    user = db.get(User, user_id)
    if user is None:
        log.warning("push: user %s not found", user_id)
        return

    row = PushOutbox(
        bot_instance_id=bot_instance_id,
        user_id=user.id,
        kind=kind,
        payload=payload,
    )
    db.add(row)
    db.flush()

    if settings.BOT_MODE == "mock":
        log.info("push[%s] queued (outbox %s)", kind, row.id)


def _next_retry_delay(attempts: int) -> timedelta:
    """Экспоненциальный backoff: 10s, 20s, 40s, …, кэп 10 мин."""
    seconds = min(_INITIAL_RETRY.total_seconds() * (2 ** (attempts - 1)), _MAX_RETRY.total_seconds())
    return timedelta(seconds=seconds)


def flush_outbox(db: Session, *, batch: int = 100) -> int:
    """Отправляет до `batch` неотправленных push-уведомлений из outbox.

    Возвращает количество УСПЕШНО отправленных. Вызывается воркером по таймеру.
    """
    from sqlalchemy import select

    now = datetime.now(tz=UTC)
    rows = list(
        db.execute(
            select(PushOutbox)
            .where(
                PushOutbox.sent_at.is_(None),
                (PushOutbox.next_retry_at.is_(None) | (PushOutbox.next_retry_at <= now)),
                PushOutbox.attempts < _MAX_ATTEMPTS,
            )
            .order_by(PushOutbox.created_at.asc())
            .limit(batch)
        ).scalars()
    )

    sent = 0
    for row in rows:
        user = db.get(User, row.user_id)
        if user is None:
            # Пользователь удалён — закрываем запись, чтобы не висела.
            row.sent_at = now
            row.last_error = "user not found"
            continue
        bot = db.get(BotInstanceRecord, row.bot_instance_id)
        if bot is None:
            row.sent_at = now
            row.last_error = "bot instance not found"
            continue

        try:
            _push_to_redis(
                _redis_item(
                    user=user,
                    bot_slug=bot.slug,
                    kind=row.kind,
                    payload=row.payload,
                )
            )
            row.sent_at = datetime.now(tz=UTC)
            row.last_error = None
            sent += 1
        except Exception as e:
            row.attempts += 1
            row.last_error = str(e)[:500]
            row.next_retry_at = datetime.now(tz=UTC) + _next_retry_delay(row.attempts)
            log.warning(
                "push: retry %s/%s failed for outbox %s: %s",
                row.attempts,
                _MAX_ATTEMPTS,
                row.id,
                e,
            )

    db.commit()
    return sent
