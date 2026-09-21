import datetime as dt
from decimal import Decimal

import pytest

from accounts.models import Organization, User
from digests.models import DailyDigest, EmailSendAttempt
from ingestion.models import IngestionRunStatus, PipelineLock
from ingestion.services.daily_pipeline import run_daily_digest_pipeline
from ingestion.services.locking import PipelineAlreadyRunningError
from intel.models import Vulnerability, VulnerabilityAIEnrichment
from taxonomy.models import TechTag, TechTagCategory, UserTechTag

NOW = dt.datetime(2026, 9, 20, 0, 0, tzinfo=dt.UTC)


def _nvd_entry(cve_id: str) -> dict:
    return {
        "cve": {
            "id": cve_id,
            "descriptions": [{"lang": "en", "value": f"Issue in {cve_id}"}],
            "vulnStatus": "Analyzed",
            "published": "2026-09-19T00:00:00.000",
            "lastModified": "2026-09-19T12:00:00.000",
            "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 9.0}}]},
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
    def fetch_catalog(self):
        return []


class StubEPSSClient:
    def fetch_scores(self, cve_ids):
        return [{"cve": cid, "epss": "0.8"} for cid in cve_ids]


class StubGeminiClient:
    model_name = "gemini-stub"

    def generate_text(self, prompt):
        return "SUMMARY: Stub summary.\nREMEDIATION: Stub remediation."


class StubResendClient:
    def __init__(self, error=None):
        self.sent = []
        self.error = error

    def send_email(self, *, from_email, to, subject, html, text):
        if self.error:
            raise self.error
        self.sent.append(to)
        return f"stub-{len(self.sent)}"


def _make_eligible_org(slug="acme"):
    org = Organization.objects.create(name="Acme", slug=slug, digest_enabled=True)
    user = User.objects.create_user(
        email=f"owner@{slug}.test", password="secret123", organization=org, is_email_verified=True
    )
    tag, _ = TechTag.objects.get_or_create(
        name="Windows Server", defaults={"category": TechTagCategory.PRODUCT}
    )
    UserTechTag.objects.create(user=user, tag=tag)
    return org


@pytest.mark.django_db
def test_daily_pipeline_end_to_end_builds_enriches_and_sends():
    org = _make_eligible_org()

    resend_client = StubResendClient()
    run = run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([_nvd_entry("CVE-2026-1111")]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=resend_client,
    )

    assert run.status == IngestionRunStatus.SUCCEEDED
    assert run.nvd_count == 1
    assert run.digest_count == 1
    assert run.candidate_count == 1

    digest = DailyDigest.objects.get(organization=org)
    assert digest.status == DailyDigest.Status.SENT
    item = digest.items.get()
    assert item.ai_summary == "Stub summary."
    assert item.ai_remediation == "Stub remediation."

    enrichment = VulnerabilityAIEnrichment.objects.get(vulnerability__cve_id="CVE-2026-1111")
    assert enrichment.summary_text == "Stub summary."

    assert EmailSendAttempt.objects.filter(daily_digest=digest, status=EmailSendAttempt.Status.SENT).exists()
    assert resend_client.sent == [org.user.email]

    # lock released after completion
    assert PipelineLock.objects.get(pk=1).is_locked is False


@pytest.mark.django_db
def test_daily_pipeline_skips_organizations_without_digest_enabled():
    org = Organization.objects.create(name="Disabled Org", slug="disabled-org", digest_enabled=False)
    User.objects.create_user(
        email="owner@disabled-org.test", password="secret123", organization=org, is_email_verified=True
    )

    run = run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(),
    )

    assert run.digest_count == 0
    assert not DailyDigest.objects.filter(organization=org).exists()


@pytest.mark.django_db
def test_daily_pipeline_skips_unverified_users_even_if_digest_enabled():
    org = Organization.objects.create(name="Unverified Org", slug="unverified-org", digest_enabled=True)
    User.objects.create_user(
        email="owner@unverified-org.test", password="secret123", organization=org, is_email_verified=False
    )

    run = run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(),
    )

    assert run.digest_count == 0


@pytest.mark.django_db
def test_daily_pipeline_continues_when_one_organization_fails(monkeypatch):
    good_org = _make_eligible_org(slug="good-org")
    bad_org = _make_eligible_org(slug="bad-org")

    import ingestion.services.daily_pipeline as daily_pipeline_module

    real_build = daily_pipeline_module.build_daily_digest

    def flaky_build(organization, **kwargs):
        if organization.slug == "bad-org":
            raise RuntimeError("simulated failure")
        return real_build(organization, **kwargs)

    monkeypatch.setattr(daily_pipeline_module, "build_daily_digest", flaky_build)

    run = run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([_nvd_entry("CVE-2026-2222")]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(),
    )

    assert run.digest_count == 1
    assert DailyDigest.objects.filter(organization=good_org).exists()
    assert not DailyDigest.objects.filter(organization=bad_org).exists()


@pytest.mark.django_db
def test_daily_pipeline_raises_when_already_locked():
    PipelineLock.objects.create(pk=1, is_locked=True)

    with pytest.raises(PipelineAlreadyRunningError):
        run_daily_digest_pipeline(
            now=NOW,
            nvd_client=StubNVDClient([]),
            kev_client=StubKEVClient(),
            epss_client=StubEPSSClient(),
            gemini_client=StubGeminiClient(),
            resend_client=StubResendClient(),
        )


@pytest.mark.django_db
def test_daily_pipeline_reuses_existing_digest_snapshot_on_rerun():
    org = _make_eligible_org()

    first_run = run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([_nvd_entry("CVE-2026-3333")]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(),
    )
    digest_id_after_first = DailyDigest.objects.get(organization=org).id

    second_run = run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(),
    )
    digest_id_after_second = DailyDigest.objects.get(organization=org).id

    assert digest_id_after_first == digest_id_after_second
    assert DailyDigest.objects.filter(organization=org).count() == 1
    # already SENT after the first run, so the same-day rerun must not resend
    assert EmailSendAttempt.objects.filter(daily_digest_id=digest_id_after_first).count() == 1


@pytest.mark.django_db
def test_daily_pipeline_retries_send_when_previous_attempt_failed():
    from digests.clients.resend import ResendClientError

    org = _make_eligible_org()

    run_daily_digest_pipeline(
        now=NOW,
        nvd_client=StubNVDClient([_nvd_entry("CVE-2026-4444")]),
        kev_client=StubKEVClient(),
        epss_client=StubEPSSClient(),
        gemini_client=StubGeminiClient(),
        resend_client=StubResendClient(error=ResendClientError("provider down")),
    )
    digest = DailyDigest.objects.get(organization=org)
    assert digest.status == DailyDigest.Status.FAILED

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
    assert EmailSendAttempt.objects.filter(daily_digest=digest).count() == 2
