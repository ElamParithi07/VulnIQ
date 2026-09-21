from io import StringIO

import pytest
from django.core.management import call_command

from ingestion.models import IngestionRun, IngestionRunStatus, IngestionRunType, PipelineLock
from ingestion.services.locking import PipelineAlreadyRunningError


@pytest.mark.django_db
def test_command_invokes_canonical_pipeline_and_reports_summary(monkeypatch):
    called_with = {}

    def fake_run(*, run_type):
        called_with["run_type"] = run_type
        return IngestionRun.objects.create(
            run_type=run_type,
            status=IngestionRunStatus.SUCCEEDED,
            nvd_count=3,
            kev_count=1,
            epss_count=3,
            candidate_count=2,
            digest_count=1,
        )

    monkeypatch.setattr(
        "ingestion.management.commands.run_daily_pipeline.run_daily_digest_pipeline", fake_run
    )

    out = StringIO()
    call_command("run_daily_pipeline", stdout=out)

    assert called_with["run_type"] == IngestionRunType.SCHEDULED
    output = out.getvalue()
    assert "completed" in output
    assert "digests=1" in output


@pytest.mark.django_db
def test_command_backfill_flag_uses_backfill_run_type(monkeypatch):
    called_with = {}

    def fake_run(*, run_type):
        called_with["run_type"] = run_type
        return IngestionRun.objects.create(run_type=run_type, status=IngestionRunStatus.SUCCEEDED)

    monkeypatch.setattr(
        "ingestion.management.commands.run_daily_pipeline.run_daily_digest_pipeline", fake_run
    )

    call_command("run_daily_pipeline", "--backfill", stdout=StringIO())

    assert called_with["run_type"] == IngestionRunType.BACKFILL


@pytest.mark.django_db
def test_command_reports_warning_when_already_running(monkeypatch):
    def fake_run(*, run_type):
        raise PipelineAlreadyRunningError("Daily pipeline is already running.")

    monkeypatch.setattr(
        "ingestion.management.commands.run_daily_pipeline.run_daily_digest_pipeline", fake_run
    )

    err = StringIO()
    call_command("run_daily_pipeline", stderr=err)

    assert "already running" in err.getvalue()


@pytest.mark.django_db
def test_command_validation_overlap_prevention_end_to_end():
    """Not mocked: proves the command surfaces the real lock, not just the
    mocked-away service."""
    PipelineLock.objects.create(pk=1, is_locked=True)

    err = StringIO()
    call_command("run_daily_pipeline", stderr=err)

    assert "already running" in err.getvalue()
