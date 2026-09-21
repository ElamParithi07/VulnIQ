import pytest
from django.core.management import call_command

from accounts.models import User


@pytest.mark.django_db
def test_creates_superuser_when_env_vars_set(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "admin@vulniq.local")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "SuperSecret123!")

    call_command("ensure_superuser")

    user = User.objects.get(email="admin@vulniq.local")
    assert user.is_superuser is True
    assert user.is_staff is True


@pytest.mark.django_db
def test_is_idempotent_when_user_already_exists(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "admin@vulniq.local")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "SuperSecret123!")

    call_command("ensure_superuser")
    call_command("ensure_superuser")

    assert User.objects.filter(email="admin@vulniq.local").count() == 1


@pytest.mark.django_db
def test_noop_when_env_vars_missing(monkeypatch):
    monkeypatch.delenv("DJANGO_SUPERUSER_EMAIL", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)

    call_command("ensure_superuser")

    assert User.objects.count() == 0
