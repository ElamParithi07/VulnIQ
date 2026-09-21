import pytest
from django.core import mail
from django.urls import reverse

from accounts.models import Organization, User


def _make_user(*, verified=False, digest_enabled=False):
    org = Organization.objects.create(name="Acme", slug="acme", digest_enabled=digest_enabled)
    user = User.objects.create_user(
        email="owner@acme.test", password="secret123", organization=org, is_email_verified=verified
    )
    return org, user


@pytest.mark.django_db
def test_dashboard_home_requires_login(client):
    response = client.get(reverse("dashboard-home"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_dashboard_home_renders_for_authenticated_user(client):
    org, user = _make_user()
    client.force_login(user)

    response = client.get(reverse("dashboard-home"))

    assert response.status_code == 200
    assert b"Acme" in response.content


@pytest.mark.django_db
def test_enable_digest_blocked_when_unverified(client):
    org, user = _make_user(verified=False)
    client.force_login(user)

    client.post(reverse("dashboard-settings"), {"action": "enable_digest"})
    org.refresh_from_db()

    assert org.digest_enabled is False


@pytest.mark.django_db
def test_enable_digest_succeeds_when_verified(client):
    org, user = _make_user(verified=True)
    client.force_login(user)

    client.post(reverse("dashboard-settings"), {"action": "enable_digest"})
    org.refresh_from_db()

    assert org.digest_enabled is True


@pytest.mark.django_db
def test_disable_digest_always_allowed(client):
    org, user = _make_user(verified=False, digest_enabled=True)
    client.force_login(user)

    client.post(reverse("dashboard-settings"), {"action": "disable_digest"})
    org.refresh_from_db()

    assert org.digest_enabled is False


@pytest.mark.django_db
def test_resend_verification_sends_email_when_unverified(client):
    org, user = _make_user(verified=False)
    client.force_login(user)

    client.post(reverse("dashboard-settings"), {"action": "resend_verification"})

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


@pytest.mark.django_db
def test_resend_verification_noop_when_already_verified(client):
    org, user = _make_user(verified=True)
    client.force_login(user)

    client.post(reverse("dashboard-settings"), {"action": "resend_verification"})

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_digest_settings_requires_login(client):
    response = client.get(reverse("dashboard-settings"))

    assert response.status_code == 302
