"""Compatibility export for the tenant-aware admission-rating worker."""

from ..modules.capabilities.admission_rating.infrastructure.sync_worker import (
    schedule_jobs,
    sync_installation,
    tick,
    tick_sync,
)

__all__ = ["schedule_jobs", "sync_installation", "tick", "tick_sync"]
