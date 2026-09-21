from __future__ import annotations

from contextlib import contextmanager

from django.db import transaction
from django.utils import timezone

from ingestion.models import PipelineLock

LOCK_ROW_PK = 1


class PipelineAlreadyRunningError(Exception):
    """Raised when the daily pipeline is already running."""


@contextmanager
def acquire_pipeline_lock():
    """DB-backed lock preventing overlapping daily pipeline runs.

    Uses a single-row lock table with select_for_update so concurrent
    callers on Postgres cannot both acquire it. Always released in a
    finally block, including when the wrapped work raises.
    """
    with transaction.atomic():
        lock, _created = PipelineLock.objects.select_for_update().get_or_create(pk=LOCK_ROW_PK)
        if lock.is_locked:
            raise PipelineAlreadyRunningError("Daily pipeline is already running.")
        lock.is_locked = True
        lock.locked_at = timezone.now()
        lock.save(update_fields=["is_locked", "locked_at", "updated_at"])

    try:
        yield
    finally:
        with transaction.atomic():
            lock = PipelineLock.objects.select_for_update().get(pk=LOCK_ROW_PK)
            lock.is_locked = False
            lock.locked_at = None
            lock.save(update_fields=["is_locked", "locked_at", "updated_at"])
