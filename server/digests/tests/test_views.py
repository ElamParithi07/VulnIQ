import datetime as dt
from decimal import Decimal

import pytest
from django.urls import reverse

from accounts.models import Organization, User
from digests.services.snapshots import build_daily_digest
from intel.models import Vulnerability, VulnerabilityProduct, VulnerabilityProductStatus, VulnerabilityStatus
from taxonomy.models import TechTag, TechTagCategory, UserTechTag

WINDOW_START = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.UTC)
WINDOW_END = dt.datetime(2026, 8, 9, 0, 0, tzinfo=dt.UTC)
IN_WINDOW = dt.datetime(2026, 8, 8, 12, 0, tzinfo=dt.UTC)
DIGEST_DATE = dt.date(2026, 8, 9)


def _make_user():
    org = Organization.objects.create(name="Acme", slug="acme")
    user = User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    return org, user


@pytest.mark.django_db
def test_latest_digest_requires_login(client):
    response = client.get(reverse("digests:latest"))

    assert response.status_code == 302


@pytest.mark.django_db
def test_latest_digest_shows_empty_state_when_none_exists(client):
    org, user = _make_user()
    client.force_login(user)

    response = client.get(reverse("digests:latest"))

    assert response.status_code == 200
    assert b"No digest has been generated yet." in response.content


@pytest.mark.django_db
def test_latest_digest_renders_snapshot_content(client):
    org, user = _make_user()
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)
    UserTechTag.objects.create(user=user, tag=tag)
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
    build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)
    client.force_login(user)

    response = client.get(reverse("digests:latest"))

    assert response.status_code == 200
    assert b"CVE-2026-0001" in response.content
    assert b"RCE in Windows Server" in response.content
