"""Точка входа воркера (APScheduler). Запускается контейнером `worker`."""

from __future__ import annotations

import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

from .. import main as _main  # noqa: F401 -- import-time side effect only: registers the
# full SQLAlchemy mapper graph (every module's presentation router pulls in its
# infrastructure models) before any job compiles a query. Without this, a job that's the
# first in this process to touch a model with a cross-module string-referenced
# relationship (e.g. User.favorited_by -> "StaffFavorite", defined in a module none of the
# other jobs happen to import) fails at query-compile time with
# `InvalidRequestError: ... failed to locate a name`, exactly as docs/development.md's own
# QA-script note already warns for standalone scripts -- this worker entrypoint has the
# same requirement, just previously unexercised. See Task 064's retention sweep, the first
# worker job to import modules/profiles/infrastructure/models.
from ..core.logging import setup_logging
from . import push_outbox as push_outbox_jobs
from .monitoring import schedule_jobs as schedule_monitoring
from .admissions_monitoring import schedule_jobs as schedule_admission
from .rut_schedule_monitoring import schedule_jobs as schedule_rut_schedule
from ..modules.consent.infrastructure.sweep import schedule_jobs as schedule_consent_retention

log = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    log.info("worker: starting APScheduler")
    scheduler = BlockingScheduler(timezone="UTC")
    # schedule_monitoring(scheduler)
    schedule_admission(scheduler)
    schedule_rut_schedule(scheduler)
    push_outbox_jobs.schedule_jobs(scheduler)
    schedule_consent_retention(scheduler)

    def _graceful(*_):
        log.info("worker: shutdown")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)

    scheduler.start()


if __name__ == "__main__":
    main()
