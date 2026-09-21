import pytest
from django.core import mail
from django.urls import reverse

from accounts.models import Organization, User


def _make_admin_client(client):
    admin_user = User.objects.create_user(
        email="admin@vulniq.local", password="secret123", is_staff=True, is_superuser=True
    )
    client.force_login(admin_user)
    return client


@pytest.mark.django_db
def test_disable_digest_sending_action(client):
    _make_admin_client(client)
    org = Organization.objects.create(name="Acme", slug="acme", digest_enabled=True)

    client.post(
        reverse("admin:accounts_organization_changelist"),
        {"action": "disable_digest_sending", "_selected_action": [str(org.pk)]},
    )
    org.refresh_from_db()

    assert org.digest_enabled is False


@pytest.mark.django_db
def test_reissue_verification_email_action_only_for_unverified(client):
    _make_admin_client(client)
    org = Organization.objects.create(name="Acme", slug="acme")
    unverified = User.objects.create_user(
        email="unverified@acme.test", password="secret123", organization=org, is_email_verified=False
    )
    verified_org = Organization.objects.create(name="Verified Co", slug="verified-co")
    verified = User.objects.create_user(
        email="verified@acme.test", password="secret123", organization=verified_org, is_email_verified=True
    )

    client.post(
        reverse("admin:accounts_user_changelist"),
        {"action": "reissue_verification_email", "_selected_action": [str(unverified.pk), str(verified.pk)]},
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [unverified.email]
