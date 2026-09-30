"""Воркер: ретраит непосланные строки push_outbox.

Запускается APScheduler-ом в `app.workers.run`. Каждые ~10 секунд берёт пачку
непосланных строк и пытается дослать в Redis. Если Redis всё ещё недоступен —
attempts++, next_retry_at += backoff.

Использует Redis-lock (как и monitoring), чтобы при нескольких репликах воркера
не было дубль-обработки.
"""

from __future__ import annotations

import logging

from ..db.redis import redis_client
from ..db.session import SessionLocal
from ..services.push import flush_outbox

log = logging.getLogger(__name__)

LOCK_KEY = "mfc:push_outbox:lock"
LOCK_TTL = 15
INTERVAL_SECONDS = 10


def tick() -> None:
    got = redis_client.set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL)
    if not got:
        return
    try:
        with SessionLocal() as db:
            sent = flush_outbox(db)
            if sent:
                log.info("push outbox: delivered %s message(s)", sent)
    finally:
        try:
            redis_client.delete(LOCK_KEY)
        except Exception as e:  # noqa: BLE001
            log.debug("push outbox lock release failed: %s", e)


def schedule_jobs(scheduler) -> None:
    scheduler.add_job(
        tick,
        "interval",
        seconds=INTERVAL_SECONDS,
        id="push_outbox_tick",
        max_instances=1,
        coalesce=True,
    )
