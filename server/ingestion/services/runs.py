from __future__ import annotations

from django.utils import timezone

from ingestion.models import IngestionRun, IngestionRunStatus, IngestionRunType


def start_run(run_type: str = IngestionRunType.SCHEDULED) -> IngestionRun:
    return IngestionRun.objects.create(run_type=run_type)


def mark_degraded(run: IngestionRun, reason: str) -> IngestionRun:
    run.is_degraded = True
    run.degraded_reason = f"{run.degraded_reason}; {reason}" if run.degraded_reason else reason
    run.save(update_fields=["is_degraded", "degraded_reason", "updated_at"])
    return run


def complete_run(
    run: IngestionRun,
    *,
    status: str = IngestionRunStatus.SUCCEEDED,
    error_message: str = "",
) -> IngestionRun:
    run.status = status
    run.completed_at = timezone.now()
    run.error_message = error_message
    run.save(update_fields=["status", "completed_at", "error_message", "updated_at"])
    return run
