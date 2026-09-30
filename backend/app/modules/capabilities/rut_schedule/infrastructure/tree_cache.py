from __future__ import annotations

import logging

from .....db.redis import redis_client

log = logging.getLogger(__name__)

# Platform-wide, matching the catalog itself (see models.py's module docstring) -- one tree for
# every bot that has rut_schedule enabled, not per-bot.
_TREE_CACHE_KEY = "platform:capability:rut_schedule:global:navigation_tree"
# Safety net only: `replace_hierarchy`'s two callers (the nightly crawl and the platform-admin
# "refresh groups" action, see sync_worker.py/manual_sync.py) call `invalidate()` right after a
# successful replace, which is the real refresh mechanism. This TTL just bounds how long a missed
# invalidation path could ever serve stale data.
_SAFETY_TTL_SECONDS = 7 * 24 * 60 * 60


class RedisScheduleTreeCache:
    """`ScheduleTreeCache` port implementation (Task 046). Never raises -- a Redis failure
    degrades to a cache miss (`get`) or a no-op (`set`/`invalidate`), never a request failure."""

    def get(self) -> str | None:
        try:
            return redis_client.get(_TREE_CACHE_KEY)
        except Exception as exc:
            log.warning("rut-schedule tree cache read failed (%s): %s", type(exc).__name__, exc)
            return None

    def set(self, payload: str) -> None:
        try:
            redis_client.set(_TREE_CACHE_KEY, payload, ex=_SAFETY_TTL_SECONDS)
        except Exception as exc:
            log.warning("rut-schedule tree cache write failed (%s): %s", type(exc).__name__, exc)

    def invalidate(self) -> None:
        try:
            redis_client.delete(_TREE_CACHE_KEY)
        except Exception as exc:
            log.warning("rut-schedule tree cache invalidate failed (%s): %s", type(exc).__name__, exc)
