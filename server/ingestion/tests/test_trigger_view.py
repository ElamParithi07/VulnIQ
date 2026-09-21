import pytest
from django.urls import reverse

from ingestion.models import IngestionRun, IngestionRunStatus, IngestionRunType, PipelineLock
from ingestion.services.locking import PipelineAlreadyRunningError


@pytest.mark.django_db
def test_trigger_requires_token(client, settings):
    settings.PIPELINE_TRIGGER_TOKEN = "secret-token"

    response = client.get(reverse("ingestion:trigger-pipeline"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_trigger_rejects_wrong_token(client, settings):
    settings.PIPELINE_TRIGGER_TOKEN = "secret-token"

    response = client.get(reverse("ingestion:trigger-pipeline"), {"token": "wrong"})

    assert response.status_code == 401


@pytest.mark.django_db
def test_trigger_rejects_when_no_token_configured(client, settings):
    settings.PIPELINE_TRIGGER_TOKEN = ""

    response = client.get(reverse("ingestion:trigger-pipeline"), {"token": ""})

    assert response.status_code == 401


@pytest.mark.django_db
def test_trigger_runs_pipeline_with_correct_token(client, settings, monkeypatch):
    settings.PIPELINE_TRIGGER_TOKEN = "secret-token"

    def fake_run(*, run_type):
        assert run_type == IngestionRunType.SCHEDULED
        return IngestionRun.objects.create(
            run_type=run_type,
            status=IngestionRunStatus.SUCCEEDED,
            nvd_count=5,
            digest_count=1,
        )

    monkeypatch.setattr("ingestion.views.run_daily_digest_pipeline", fake_run)

    response = client.get(reverse("ingestion:trigger-pipeline"), {"token": "secret-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["nvd_count"] == 5
    assert body["digest_count"] == 1


@pytest.mark.django_db
def test_trigger_accepts_post_too(client, settings, monkeypatch):
    settings.PIPELINE_TRIGGER_TOKEN = "secret-token"

    monkeypatch.setattr(
        "ingestion.views.run_daily_digest_pipeline",
        lambda *, run_type: IngestionRun.objects.create(run_type=run_type, status=IngestionRunStatus.SUCCEEDED),
    )

    response = client.post(reverse("ingestion:trigger-pipeline"), {"token": "secret-token"})

    assert response.status_code == 200


@pytest.mark.django_db
def test_trigger_returns_409_when_already_running(client, settings):
    settings.PIPELINE_TRIGGER_TOKEN = "secret-token"
    PipelineLock.objects.create(pk=1, is_locked=True)

    response = client.get(reverse("ingestion:trigger-pipeline"), {"token": "secret-token"})

    assert response.status_code == 409
