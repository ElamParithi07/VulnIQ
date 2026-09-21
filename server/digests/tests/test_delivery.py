import datetime as dt
from decimal import Decimal

import pytest

from accounts.models import Organization, User
from digests.clients.resend import ResendClientError
from digests.models import DailyDigest, EmailSendAttempt
from digests.services.delivery import send_digest
from digests.services.snapshots import build_daily_digest
from intel.models import Vulnerability, VulnerabilityProduct, VulnerabilityProductStatus, VulnerabilityStatus
from taxonomy.models import TechTag, TechTagCategory, UserTechTag

WINDOW_START = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.UTC)
WINDOW_END = dt.datetime(2026, 8, 9, 0, 0, tzinfo=dt.UTC)
IN_WINDOW = dt.datetime(2026, 8, 8, 12, 0, tzinfo=dt.UTC)
DIGEST_DATE = dt.date(2026, 8, 9)


class StubResendClient:
    def __init__(self, message_id=None, error=None):
        self.message_id = message_id
        self.error = error
        self.calls = []

    def send_email(self, *, from_email, to, subject, html, text):
        self.calls.append({"from_email": from_email, "to": to, "subject": subject, "html": html, "text": text})
        if self.error:
            raise self.error
        return self.message_id


def _make_digest():
    org = Organization.objects.create(name="Acme", slug="acme")
    User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)
    UserTechTag.objects.create(user=org.user, tag=tag)
    vulnerability = Vulnerability.objects.create(
        cve_id="CVE-2026-0001",
        title="RCE in Windows Server",
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
def test_send_digest_success_persists_attempt_and_marks_sent():
    digest = _make_digest()
    client = StubResendClient(message_id="msg-1")

    attempt = send_digest(digest, client=client)
    digest.refresh_from_db()

    assert attempt.status == EmailSendAttempt.Status.SENT
    assert attempt.attempt_number == 1
    assert attempt.provider_message_id == "msg-1"
    assert digest.status == DailyDigest.Status.SENT
    assert digest.sent_at is not None
    assert digest.rendered_subject
    assert "CVE-2026-0001" in digest.rendered_html
    assert "CVE-2026-0001" in digest.rendered_text


@pytest.mark.django_db
def test_send_digest_failure_persists_failed_attempt_and_marks_digest_failed():
    digest = _make_digest()
    client = StubResendClient(error=ResendClientError("provider down"))

    attempt = send_digest(digest, client=client)
    digest.refresh_from_db()

    assert attempt.status == EmailSendAttempt.Status.FAILED
    assert "provider down" in attempt.error_message
    assert digest.status == DailyDigest.Status.FAILED
    assert digest.sent_at is None


@pytest.mark.django_db
def test_retry_reuses_same_rendered_snapshot_content():
    digest = _make_digest()
    failing_client = StubResendClient(error=ResendClientError("temporary outage"))
    send_digest(digest, client=failing_client)
    digest.refresh_from_db()
    rendered_html_after_failure = digest.rendered_html

    working_client = StubResendClient(message_id="msg-2")
    attempt = send_digest(digest, client=working_client)
    digest.refresh_from_db()

    assert working_client.calls[0]["html"] == rendered_html_after_failure
    assert digest.rendered_html == rendered_html_after_failure
    assert attempt.attempt_number == 2
    assert digest.status == DailyDigest.Status.SENT


@pytest.mark.django_db
def test_retry_after_success_does_not_overwrite_sent_at():
    digest = _make_digest()
    client = StubResendClient(message_id="msg-1")
    send_digest(digest, client=client)
    digest.refresh_from_db()
    first_sent_at = digest.sent_at

    second_client = StubResendClient(message_id="msg-2")
    send_digest(digest, client=second_client)
    digest.refresh_from_db()

    assert digest.sent_at == first_sent_at
    assert EmailSendAttempt.objects.filter(daily_digest=digest).count() == 2


@pytest.mark.django_db
def test_multiple_attempts_get_sequential_attempt_numbers():
    digest = _make_digest()

    send_digest(digest, client=StubResendClient(error=ResendClientError("down")))
    send_digest(digest, client=StubResendClient(error=ResendClientError("down again")))
    send_digest(digest, client=StubResendClient(message_id="msg-final"))

    attempt_numbers = list(
        EmailSendAttempt.objects.filter(daily_digest=digest).order_by("attempt_number").values_list(
            "attempt_number", flat=True
        )
    )
    assert attempt_numbers == [1, 2, 3]
