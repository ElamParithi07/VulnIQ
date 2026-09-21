import pytest
from freezegun import freeze_time

from ingestion.models import IngestionRun, IngestionRunStatus, IngestionRunType


@pytest.mark.django_db
def test_ingestion_run_defaults():
    run = IngestionRun.objects.create()

    assert run.run_type == IngestionRunType.SCHEDULED
    assert run.status == IngestionRunStatus.RUNNING
    assert run.is_degraded is False
    assert run.started_at is not None
    assert run.completed_at is None
    assert run.nvd_count == 0


@pytest.mark.django_db
def test_ingestion_run_can_be_marked_degraded_with_reason():
    run = IngestionRun.objects.create(run_type=IngestionRunType.SCHEDULED)

    run.is_degraded = True
    run.degraded_reason = "KEV source unavailable"
    run.status = IngestionRunStatus.SUCCEEDED
    run.save()
    run.refresh_from_db()

    assert run.is_degraded is True
    assert run.degraded_reason == "KEV source unavailable"
    assert run.status == IngestionRunStatus.SUCCEEDED


@pytest.mark.django_db
def test_ingestion_runs_ordered_most_recent_first():
    with freeze_time("2026-08-09 00:00:00"):
        older = IngestionRun.objects.create()

    with freeze_time("2026-08-10 00:00:00"):
        newer = IngestionRun.objects.create()

    assert list(IngestionRun.objects.values_list("id", flat=True)) == [newer.id, older.id]
