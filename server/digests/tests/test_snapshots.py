import datetime as dt
from decimal import Decimal

import pytest

from accounts.models import Organization, User
from digests.models import DailyDigest, DailyDigestItem
from digests.services.query import get_latest_digest
from digests.services.snapshots import build_daily_digest
from intel.models import (
    Vulnerability,
    VulnerabilityAIEnrichment,
    VulnerabilityProduct,
    VulnerabilityProductStatus,
    VulnerabilityStatus,
)
from taxonomy.models import TechTag, TechTagCategory, UserTechTag

WINDOW_START = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.UTC)
WINDOW_END = dt.datetime(2026, 8, 9, 0, 0, tzinfo=dt.UTC)
IN_WINDOW = dt.datetime(2026, 8, 8, 12, 0, tzinfo=dt.UTC)
DIGEST_DATE = dt.date(2026, 8, 9)


def _make_org():
    org = Organization.objects.create(name="Acme", slug="acme")
    User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    return org


def _make_matched_vulnerability(org, cve_id="CVE-2026-0001", priority_score="9.0"):
    tag, _created = TechTag.objects.get_or_create(
        name="Windows Server", defaults={"category": TechTagCategory.PRODUCT}
    )
    UserTechTag.objects.get_or_create(user=org.user, tag=tag)
    vulnerability = Vulnerability.objects.create(
        cve_id=cve_id,
        status=VulnerabilityStatus.PUBLISHED,
        priority_score=Decimal(priority_score),
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
    return vulnerability


@pytest.mark.django_db
def test_build_daily_digest_creates_snapshot_with_ranked_items():
    org = _make_org()
    _make_matched_vulnerability(org)

    digest = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)

    assert digest is not None
    assert digest.status == DailyDigest.Status.READY
    assert digest.matching_vulnerability_count == 1
    assert digest.backfill_vulnerability_count == 0

    items = list(digest.items.all())
    assert len(items) == 1
    assert items[0].rank == 1
    assert items[0].cve_id == "CVE-2026-0001"
    assert items[0].is_backfill is False


@pytest.mark.django_db
def test_build_daily_digest_freezes_ai_enrichment_into_item():
    org = _make_org()
    vulnerability = _make_matched_vulnerability(org)
    VulnerabilityAIEnrichment.objects.create(
        vulnerability=vulnerability,
        provider="gemini",
        model_name="gemini-2.5-flash",
        prompt_version="v1",
        input_hash="abc123",
        summary_text="Summary text",
        remediation_text="Remediation text",
    )

    digest = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)

    item = digest.items.get()
    assert item.ai_summary == "Summary text"
    assert item.ai_remediation == "Remediation text"


@pytest.mark.django_db
def test_build_daily_digest_is_idempotent_and_immutable_on_rerun():
    org = _make_org()
    _make_matched_vulnerability(org)

    first = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)
    first_item_id = first.items.get().id

    # simulate a later rerun of the pipeline for the same business date after
    # new data has landed
    _make_matched_vulnerability(org, cve_id="CVE-2026-9999", priority_score="9.9")
    second = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)

    assert second.id == first.id
    assert DailyDigest.objects.filter(organization=org, digest_date=DIGEST_DATE).count() == 1
    assert list(second.items.values_list("id", flat=True)) == [first_item_id]


@pytest.mark.django_db
def test_build_daily_digest_returns_none_when_no_candidates():
    org = _make_org()

    digest = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)

    assert digest is None
    assert DailyDigest.objects.count() == 0


@pytest.mark.django_db
def test_build_daily_digest_returns_none_without_eligible_user():
    org = Organization.objects.create(name="Ghost Org", slug="ghost-org")

    digest = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)

    assert digest is None


@pytest.mark.django_db
def test_get_latest_digest_returns_most_recent_by_date():
    org = _make_org()
    _make_matched_vulnerability(org)
    build_daily_digest(org, digest_date=dt.date(2026, 8, 7), window_start=WINDOW_START, window_end=WINDOW_END)
    newest = build_daily_digest(
        org, digest_date=dt.date(2026, 8, 9), window_start=WINDOW_START, window_end=WINDOW_END
    )

    latest = get_latest_digest(org)

    assert latest.id == newest.id
    assert latest.digest_date == dt.date(2026, 8, 9)


@pytest.mark.django_db
def test_get_latest_digest_returns_none_when_no_digests_exist():
    org = _make_org()

    assert get_latest_digest(org) is None
