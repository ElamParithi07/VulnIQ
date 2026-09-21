"""True end-to-end tests chaining multiple modules through their real
entrypoints (HTTP views where they exist, service functions for backend-only
work), per the Milestone 6 hardening scope. Unit/integration coverage for
each individual piece already lives in each app's own tests/ package; these
tests exist to catch regressions in how the pieces fit together.
"""
from __future__ import annotations

import datetime as dt

import pytest
from django.core import mail
from django.urls import reverse

from accounts.models import EmailVerificationToken, Organization, User
from digests.clients.resend import ResendClientError
from digests.models import DailyDigest, EmailSendAttempt
from ingestion.clients import EPSSClientError, KEVClientError
from ingestion.models import IngestionRunStatus
from ingestion.services.daily_pipeline import run_daily_digest_pipeline
from taxonomy.models import TechTag, TechTagCategory, UserTechTag
from tests.factories import OrganizationFactory, TechTagFactory, UserFactory

NOW = dt.datetime(2026, 9, 21, 0, 0, tzinfo=dt.UTC)


def _nvd_entry(cve_id: str, *, cvss: float = 9.0) -> dict:
    return {
        "cve": {
            "id": cve_id,
            "descriptions": [{"lang": "en", "value": f"Issue in {cve_id}"}],
            "vulnStatus": "Analyzed",
            "published": "2026-09-20T00:00:00.000",
            "lastModified": "2026-09-20T12:00:00.000",
            "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": cvss}}]},
            "configurations": [
                {
                    "nodes": [
                        {
                            "cpeMatch": [
                                {
                                    "criteria": "cpe:2.3:a:microsoft:windows_server:2022:*:*:*:*:*:*:*",
                                    "vulnerable": True,
                                }
                            ]
                        }
                    ]
                }
            ],
        }
    }


class StubNVDClient:
    def __init__(self, entries):
        self.entries = entries

    def fetch_modified_between(self, *, start, end, start_index=0):
        return self.entries


class StubKEVClient:
    def __init__(self, entries=None, error=None):
        self.entries = entries or []
        self.error = error

    def fetch_catalog(self):
        if self.error:
            raise self.error
        return self.entries


class StubEPSSClient:
    def __init__(self, error=None):
        self.error = error

    def fetch_scores(self, cve_ids):
        if self.error:
            raise self.error
        return [{"cve": cid, "epss": "0.7"} for cid in cve_ids]


class StubGeminiClient:
    model_name = "gemini-stub"

    def generate_text(self, prompt):
        return "SUMMARY: Stub summary.\nREMEDIATION: Stub remediation."


class StubResendClient:
    def __init__(self, error=None):
        self.sent_to = []
        self.error = error

    def send_email(self, *, from_email, to, subject, html, text):
        if self.error:
            raise self.error
        self.sent_to.append(to)
        return f"stub-{len(self.sent_to)}"


def _make_eligible_org_with_tag(*, slug: str, tag_name: str = "Windows Server") -> tuple[Organization, TechTag]:
    """Org with digest_enabled=True, a verified user, and one selected tag."""
    org = OrganizationFactory(slug=slug, digest_enabled=True)
    user = UserFactory(organization=org, is_email_verified=True)
    tag = TechTagFactory(name=tag_name)
    UserTechTag.objects.create(user=user, tag=tag)
    return org, tag


@pytest.mark.django_db
def test_signup_verify_select_tags_enable_digest_flow(client):
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)

    # 1. signup
    response = client.post(
        reverse("accounts:signup"),
        {
            "organization_name": "E2E Org",
            "organization_slug": "e2e-org",
            "email": "e2e@acme.test",
            "password1": "SuperSecret123",
            "password2": "SuperSecret123",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(email="e2e@acme.test")
    assert user.is_email_verified is False
    assert len(mail.outbox) == 1

    # 2. attempting to enable digest before verification is blocked
    client.post(reverse("dashboard-settings"), {"action": "enable_digest"})
    user.organization.refresh_from_db()
    assert user.organization.digest_enabled is False

    # 3. verify email via the real link
    token = EmailVerificationToken.objects.get(user=user)
    response = client.get(reverse("accounts:verify-email", kwargs={"token": token.token}))
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.is_email_verified is True

    # 4. select a product tag
    client.post(reverse("taxonomy:tag-selection"), {"tags": [str(tag.id)]})
    assert set(user.selected_tech_tags.values_list("tag_id", flat=True)) == {tag.id}

    # 5. enable digest now succeeds
    client.post(reverse("dashboard-settings"), {"action": "enable_digest"})
    user.organization.refresh_from_db()
    assert user.organization.digest_enabled is True

    # 6. dashboard and latest-digest page both render without error
    assert client.get(reverse("dashboard-home")).status_code == 200
    assert client.get(reverse("digests:latest")).status_code == 200


@pytest.mark.django_db
def test_ingestion_through_matching_scoring_snapshot_and_send(client):
    org, _tag = _make_eligible_org_with_tag(slug="pipeline-org")

    resend_client = StubResendClient()
    run = run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([_nvd_entry("CVE-2026-10001", cvss=9.5)]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=resend_client,
    )

    assert run.status == IngestionRunStatus.SUCCEEDED
    assert run.nvd_count == 1

    digest = DailyDigest.objects.get(organization=org)
    assert digest.status == DailyDigest.Status.SENT
    item = digest.items.get()
    assert item.cve_id == "CVE-2026-10001"
    assert item.is_backfill is False  # direct tag match, not global backfill
    assert item.ai_summary == "Stub summary."
    assert resend_client.sent_to == [org.user.email]


@pytest.mark.django_db
def test_zero_direct_match_produces_backfill_note_in_email():
    # org's selected tag ("VMware vCenter") matches nothing in the ingested
    # CVE below, so this should fall through to pure global backfill
    org, _selected_tag = _make_eligible_org_with_tag(slug="no-match-org", tag_name="VMware vCenter")
    TechTagFactory(name="Windows Server")

    run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([_nvd_entry("CVE-2026-20002", cvss=9.9)]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(),
    )

    digest = DailyDigest.objects.get(organization=org)
    assert digest.matching_vulnerability_count == 0
    assert digest.backfill_vulnerability_count == 1
    assert "top global threats instead" in digest.rendered_html
    assert "top global threats instead" in digest.rendered_text


@pytest.mark.django_db
def test_degraded_kev_source_marks_run_degraded_but_still_completes():
    org, _tag = _make_eligible_org_with_tag(slug="degraded-org")

    run = run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([_nvd_entry("CVE-2026-30003")]),
        kev_client=StubKEVClient(error=KEVClientError("KEV feed unavailable")),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(),
    )

    assert run.status == IngestionRunStatus.SUCCEEDED
    assert run.is_degraded is True
    assert "KEV fetch failed" in run.degraded_reason
    # degraded source doesn't block the rest of the pipeline
    assert DailyDigest.objects.filter(organization=org, status=DailyDigest.Status.SENT).exists()


@pytest.mark.django_db
def test_epss_source_failure_also_degrades_run_without_blocking_digest():
    org, _tag = _make_eligible_org_with_tag(slug="epss-degraded-org")

    run = run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([_nvd_entry("CVE-2026-40004")]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(error=EPSSClientError("EPSS API unavailable")),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(),
    )

    assert run.is_degraded is True
    assert "EPSS fetch failed" in run.degraded_reason
    assert DailyDigest.objects.filter(organization=org, status=DailyDigest.Status.SENT).exists()


@pytest.mark.django_db
def test_retry_send_reuses_same_snapshot_content_end_to_end():
    org, _tag = _make_eligible_org_with_tag(slug="retry-org")

    # first run: email delivery fails
    run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([_nvd_entry("CVE-2026-50005")]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(error=ResendClientError("provider outage")),
    )
    digest = DailyDigest.objects.get(organization=org)
    assert digest.status == DailyDigest.Status.FAILED
    rendered_html_after_failure = digest.rendered_html
    rendered_subject_after_failure = digest.rendered_subject

    # second run same business day: NVD has nothing new, but the failed send
    # must still be retried against the *same* snapshot content
    run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(),
    )
    digest.refresh_from_db()

    assert digest.status == DailyDigest.Status.SENT
    assert digest.rendered_html == rendered_html_after_failure
    assert digest.rendered_subject == rendered_subject_after_failure
    assert EmailSendAttempt.objects.filter(daily_digest=digest).count() == 2
    attempt_numbers = list(
        EmailSendAttempt.objects.filter(daily_digest=digest)
        .order_by("attempt_number")
        .values_list("attempt_number", flat=True)
    )
    assert attempt_numbers == [1, 2]
