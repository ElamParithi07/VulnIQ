import pytest
from django.core import mail
from django.urls import reverse

from accounts.models import EmailVerificationToken, Organization, User
from accounts.services.verification import issue_email_verification_token


@pytest.mark.django_db
def test_user_email_is_unique():
    org = Organization.objects.create(name="Acme", slug="acme")
    User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)

    with pytest.raises(Exception):
        User.objects.create_user(email="owner@acme.test", password="secret123")


@pytest.mark.django_db
def test_user_can_enable_digests_only_after_verification():
    user = User.objects.create_user(email="owner@acme.test", password="secret123")

    assert user.can_enable_digests is False

    user.is_email_verified = True

    assert user.can_enable_digests is True


@pytest.mark.django_db
def test_email_verification_token_is_active_before_expiry():
    user = User.objects.create_user(email="owner@acme.test", password="secret123")
    token = EmailVerificationToken.objects.create(
        user=user,
        token="abc123",
        expires_at=EmailVerificationToken.build_expiry(),
    )

    assert token.is_active is True


@pytest.mark.django_db
def test_signup_creates_org_and_sends_verification_email(client):
    response = client.post(
        reverse("accounts:signup"),
        data={
            "organization_name": "Acme",
            "organization_slug": "acme",
            "email": "owner@acme.test",
            "password1": "secret12345",
            "password2": "secret12345",
        },
    )

    assert response.status_code == 302
    assert User.objects.filter(email="owner@acme.test", organization__slug="acme").exists()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_email_verification_view_marks_user_verified(client):
    user = User.objects.create_user(email="owner@acme.test", password="secret123")
    token = issue_email_verification_token(user)

    response = client.get(reverse("accounts:verify-email", kwargs={"token": token.token}))
    user.refresh_from_db()

    assert response.status_code == 302
    assert user.is_email_verified is True
