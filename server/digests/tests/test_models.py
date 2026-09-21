import datetime as dt

import pytest
from django.db import IntegrityError

from accounts.models import Organization, User
from digests.models import DailyDigest, DailyDigestItem


@pytest.mark.django_db
def test_daily_digest_is_unique_per_organization_and_day():
    org = Organization.objects.create(name="Acme", slug="acme")
    user = User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    DailyDigest.objects.create(organization=org, user=user, digest_date=dt.date(2026, 8, 9))

    with pytest.raises(IntegrityError):
        DailyDigest.objects.create(organization=org, user=user, digest_date=dt.date(2026, 8, 9))


@pytest.mark.django_db
def test_digest_item_rank_is_unique_within_digest():
    org = Organization.objects.create(name="Acme", slug="acme")
    user = User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    digest = DailyDigest.objects.create(organization=org, user=user, digest_date=dt.date(2026, 8, 9))
    vulnerability = _create_vulnerability()

    DailyDigestItem.objects.create(
        daily_digest=digest,
        vulnerability=vulnerability,
        rank=1,
        vendor_name="microsoft",
        product_name="windows",
        cve_id="CVE-2026-0001",
    )

    with pytest.raises(IntegrityError):
        DailyDigestItem.objects.create(
            daily_digest=digest,
            vulnerability=_create_vulnerability(cve_id="CVE-2026-0002"),
            rank=1,
            vendor_name="apache",
            product_name="http_server",
            cve_id="CVE-2026-0002",
        )


@pytest.mark.django_db
def test_digest_item_vulnerability_is_unique_within_digest():
    org = Organization.objects.create(name="Acme", slug="acme")
    user = User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    digest = DailyDigest.objects.create(organization=org, user=user, digest_date=dt.date(2026, 8, 9))
    vulnerability = _create_vulnerability()

    DailyDigestItem.objects.create(
        daily_digest=digest,
        vulnerability=vulnerability,
        rank=1,
        vendor_name="microsoft",
        product_name="windows",
        cve_id="CVE-2026-0001",
    )

    with pytest.raises(IntegrityError):
        DailyDigestItem.objects.create(
            daily_digest=digest,
            vulnerability=vulnerability,
            rank=2,
            vendor_name="microsoft",
            product_name="windows",
            cve_id="CVE-2026-0001",
        )


def _create_vulnerability(cve_id: str = "CVE-2026-0001"):
    from intel.models import Vulnerability, VulnerabilityStatus

    return Vulnerability.objects.create(
        cve_id=cve_id,
        title="Remote code execution issue",
        description="Remote code execution issue",
        published_at=dt.datetime(2026, 8, 8, 12, 0, tzinfo=dt.UTC),
        last_modified_at=dt.datetime(2026, 8, 9, 12, 0, tzinfo=dt.UTC),
        status=VulnerabilityStatus.PUBLISHED,
        cvss_score=9.8,
        epss_score=0.93,
        is_cisa_kev=True,
        priority_score=6.82,
    )
