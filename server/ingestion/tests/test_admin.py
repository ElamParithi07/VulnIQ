import pytest
from django.urls import reverse

from accounts.models import User
from ingestion.models import IngestionRun, IngestionRunStatus, IngestionRunType, PipelineLock


def _make_admin_client(client):
    admin_user = User.objects.create_user(
        email="admin@vulniq.local", password="secret123", is_staff=True, is_superuser=True
    )
    client.force_login(admin_user)
    return client


@pytest.mark.django_db
def test_trigger_get_shows_confirmation_page(client):
    _make_admin_client(client)

    response = client.get(reverse("admin:ingestion_ingestionrun_trigger"))

    assert response.status_code == 200
    assert b"Run daily pipeline now" in response.content


@pytest.mark.django_db
def test_trigger_post_runs_canonical_pipeline(client, monkeypatch):
    _make_admin_client(client)

    def fake_run(*, run_type):
        assert run_type == IngestionRunType.MANUAL
        return IngestionRun.objects.create(run_type=run_type, status=IngestionRunStatus.SUCCEEDED, digest_count=2)

    monkeypatch.setattr("ingestion.services.daily_pipeline.run_daily_digest_pipeline", fake_run)

    response = client.post(reverse("admin:ingestion_ingestionrun_trigger"), follow=True)

    assert response.status_code == 200
    assert b"completed" in response.content


@pytest.mark.django_db
def test_trigger_post_reports_when_already_running(client):
    _make_admin_client(client)
    PipelineLock.objects.create(pk=1, is_locked=True)

    response = client.post(reverse("admin:ingestion_ingestionrun_trigger"), follow=True)

    assert response.status_code == 200
    assert b"already running" in response.content
