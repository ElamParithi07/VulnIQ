import pytest

from ingestion.models import IngestionRunStatus
from ingestion.services.runs import complete_run, mark_degraded, start_run


@pytest.mark.django_db
def test_start_run_creates_running_record():
    run = start_run()

    assert run.status == IngestionRunStatus.RUNNING
    assert run.completed_at is None


@pytest.mark.django_db
def test_mark_degraded_sets_flag_and_reason():
    run = start_run()

    mark_degraded(run, "KEV fetch failed")
    run.refresh_from_db()

    assert run.is_degraded is True
    assert run.degraded_reason == "KEV fetch failed"


@pytest.mark.django_db
def test_mark_degraded_accumulates_multiple_reasons():
    run = start_run()

    mark_degraded(run, "KEV fetch failed")
    mark_degraded(run, "EPSS fetch failed")
    run.refresh_from_db()

    assert run.degraded_reason == "KEV fetch failed; EPSS fetch failed"


@pytest.mark.django_db
def test_complete_run_sets_status_and_completed_at():
    run = start_run()

    complete_run(run, status=IngestionRunStatus.SUCCEEDED)
    run.refresh_from_db()

    assert run.status == IngestionRunStatus.SUCCEEDED
    assert run.completed_at is not None


@pytest.mark.django_db
def test_complete_run_records_error_message_on_failure():
    run = start_run()

    complete_run(run, status=IngestionRunStatus.FAILED, error_message="boom")
    run.refresh_from_db()

    assert run.status == IngestionRunStatus.FAILED
    assert run.error_message == "boom"
