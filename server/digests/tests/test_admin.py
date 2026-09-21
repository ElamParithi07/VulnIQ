import datetime as dt
from decimal import Decimal

import pytest
from django.urls import reverse

from accounts.models import Organization, User
from digests.clients.resend import ResendClientError
from digests.models import DailyDigest, EmailSendAttempt
from digests.services.snapshots import build_daily_digest
from intel.models import Vulnerability, VulnerabilityProduct, VulnerabilityProductStatus, VulnerabilityStatus
from taxonomy.models import TechTag, TechTagCategory, UserTechTag

WINDOW_START = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.UTC)
WINDOW_END = dt.datetime(2026, 8, 9, 0, 0, tzinfo=dt.UTC)
IN_WINDOW = dt.datetime(2026, 8, 8, 12, 0, tzinfo=dt.UTC)
DIGEST_DATE = dt.date(2026, 8, 9)


def _make_admin_client(client):
    admin_user = User.objects.create_user(
        email="admin@vulniq.local", password="secret123", is_staff=True, is_superuser=True
    )
    client.force_login(admin_user)
    return client


def _make_digest():
    org = Organization.objects.create(name="Acme", slug="acme")
    User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)
    UserTechTag.objects.create(user=org.user, tag=tag)
    vulnerability = Vulnerability.objects.create(
        cve_id="CVE-2026-0001",
        status=VulnerabilityStatus.PUBLISHED,
        priority_score=Decimal("9.0"),
        cvss_score=Decimal("9.0"),
        last_modified_at=IN_WINDOW,
    )
    VulnerabilityProduct.objects.create(
        vulnerability=vulnerability,
        raw_vendor="microsoft",
        raw_product="windows server",
        normalized_vendor="microsoft",
        normalized_product="windows server",
        tech_tag=tag,
        match_status=VulnerabilityProductStatus.MATCHED,
    )
    return build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)


@pytest.mark.django_db
def test_resend_digest_email_action_success(client, monkeypatch):
    _make_admin_client(client)
    digest = _make_digest()

    monkeypatch.setattr(
        "digests.clients.resend.ResendClient.send_email",
        lambda self, **kwargs: "stub-message-id",
    )

    client.post(
        reverse("admin:digests_dailydigest_changelist"),
        {"action": "resend_digest_email", "_selected_action": [str(digest.pk)]},
    )
    digest.refresh_from_db()

    assert digest.status == DailyDigest.Status.SENT
    assert EmailSendAttempt.objects.filter(daily_digest=digest, status=EmailSendAttempt.Status.SENT).exists()


@pytest.mark.django_db
def test_resend_digest_email_action_records_failure(client, monkeypatch):
    _make_admin_client(client)
    digest = _make_digest()

    def raise_error(self, **kwargs):
        raise ResendClientError("provider down")

    monkeypatch.setattr("digests.clients.resend.ResendClient.send_email", raise_error)

    client.post(
        reverse("admin:digests_dailydigest_changelist"),
        {"action": "resend_digest_email", "_selected_action": [str(digest.pk)]},
    )
    digest.refresh_from_db()

    assert digest.status == DailyDigest.Status.FAILED
    assert EmailSendAttempt.objects.filter(daily_digest=digest, status=EmailSendAttempt.Status.FAILED).exists()
