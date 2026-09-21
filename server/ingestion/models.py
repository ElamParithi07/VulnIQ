from django.db import models

from common.models import TimeStampedModel


class IngestionRunType(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    MANUAL = "manual", "Manual"
    BACKFILL = "backfill", "Backfill"


class IngestionRunStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class IngestionRun(TimeStampedModel):
    run_type = models.CharField(
        max_length=20,
        choices=IngestionRunType.choices,
        default=IngestionRunType.SCHEDULED,
    )
    status = models.CharField(
        max_length=20,
        choices=IngestionRunStatus.choices,
        default=IngestionRunStatus.RUNNING,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_degraded = models.BooleanField(default=False)
    degraded_reason = models.TextField(blank=True)
    nvd_count = models.PositiveIntegerField(default=0)
    kev_count = models.PositiveIntegerField(default=0)
    epss_count = models.PositiveIntegerField(default=0)
    candidate_count = models.PositiveIntegerField(default=0)
    digest_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["status"], name="ingestion_run_status_idx"),
            models.Index(fields=["started_at"], name="ingestion_run_started_idx"),
        ]

    def __str__(self) -> str:
        return f"IngestionRun#{self.pk} [{self.run_type}/{self.status}]"


class PipelineLock(TimeStampedModel):
    """Singleton row (pk=1) used as a DB-backed lock to prevent overlapping
    daily pipeline runs."""

    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"PipelineLock(locked={self.is_locked})"
