import datetime as dt
from decimal import Decimal

import pytest

from accounts.models import Organization, User
from digests.services.selection import MAX_DIGEST_ITEMS, select_candidates_for_organization
from intel.models import Vulnerability, VulnerabilityProduct, VulnerabilityProductStatus, VulnerabilityStatus
from taxonomy.models import TechTag, TechTagCategory, UserTechTag

WINDOW_START = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.UTC)
WINDOW_END = dt.datetime(2026, 8, 9, 0, 0, tzinfo=dt.UTC)
IN_WINDOW = dt.datetime(2026, 8, 8, 12, 0, tzinfo=dt.UTC)
OUT_OF_WINDOW = dt.datetime(2026, 8, 1, 0, 0, tzinfo=dt.UTC)


def _make_org_with_tags(*tags):
    org = Organization.objects.create(name="Acme", slug="acme")
    user = User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    for tag in tags:
        UserTechTag.objects.create(user=user, tag=tag)
    return org


def _make_tag(name="Windows Server"):
    return TechTag.objects.create(name=name, category=TechTagCategory.PRODUCT)


def _make_vulnerability(cve_id, *, priority_score, last_modified_at=IN_WINDOW, status=VulnerabilityStatus.PUBLISHED):
    return Vulnerability.objects.create(
        cve_id=cve_id,
        status=status,
        priority_score=Decimal(str(priority_score)),
        last_modified_at=last_modified_at,
    )


def _make_matched_product(vulnerability, tag, vendor="microsoft", product="windows server"):
    return VulnerabilityProduct.objects.create(
        vulnerability=vulnerability,
        raw_vendor=vendor,
        raw_product=product,
        normalized_vendor=vendor,
        normalized_product=product,
        tech_tag=tag,
        match_status=VulnerabilityProductStatus.MATCHED,
    )


@pytest.mark.django_db
def test_direct_matches_are_ranked_by_priority_score_descending():
    tag = _make_tag()
    org = _make_org_with_tags(tag)

    low = _make_vulnerability("CVE-2026-0001", priority_score="3.0")
    high = _make_vulnerability("CVE-2026-0002", priority_score="9.0")
    _make_matched_product(low, tag)
    _make_matched_product(high, tag)

    results = select_candidates_for_organization(org, window_start=WINDOW_START, window_end=WINDOW_END)

    assert [c.vulnerability.cve_id for c in results] == ["CVE-2026-0002", "CVE-2026-0001"]
    assert all(not c.is_backfill for c in results)


@pytest.mark.django_db
def test_backfill_fills_remaining_slots_when_direct_matches_are_few():
    tag = _make_tag()
    org = _make_org_with_tags(tag)

    matched = _make_vulnerability("CVE-2026-0001", priority_score="9.0")
    _make_matched_product(matched, tag)

    backfill = _make_vulnerability("CVE-2026-0002", priority_score="8.0")

    results = select_candidates_for_organization(org, window_start=WINDOW_START, window_end=WINDOW_END)

    assert len(results) == 2
    assert results[0].vulnerability.cve_id == "CVE-2026-0001"
    assert results[0].is_backfill is False
    assert results[1].vulnerability.cve_id == "CVE-2026-0002"
    assert results[1].is_backfill is True


@pytest.mark.django_db
def test_zero_direct_matches_uses_pure_backfill():
    tag = _make_tag()
    org = _make_org_with_tags(tag)

    _make_vulnerability("CVE-2026-0001", priority_score="7.5")

    results = select_candidates_for_organization(org, window_start=WINDOW_START, window_end=WINDOW_END)

    assert len(results) == 1
    assert results[0].is_backfill is True


@pytest.mark.django_db
def test_no_candidates_at_all_returns_empty_list():
    tag = _make_tag()
    org = _make_org_with_tags(tag)

    results = select_candidates_for_organization(org, window_start=WINDOW_START, window_end=WINDOW_END)

    assert results == []


@pytest.mark.django_db
def test_duplicate_cve_across_multiple_tags_is_included_once():
    tag_a = _make_tag("Windows Server")
    tag_b = _make_tag("VMware vCenter")
    org = _make_org_with_tags(tag_a, tag_b)

    vulnerability = _make_vulnerability("CVE-2026-0001", priority_score="9.0")
    _make_matched_product(vulnerability, tag_a, vendor="microsoft", product="windows server")
    _make_matched_product(vulnerability, tag_b, vendor="vmware", product="vcenter")

    results = select_candidates_for_organization(org, window_start=WINDOW_START, window_end=WINDOW_END)

    assert len(results) == 1
    assert results[0].vulnerability.cve_id == "CVE-2026-0001"


@pytest.mark.django_db
def test_results_are_capped_at_limit():
    tag = _make_tag()
    org = _make_org_with_tags(tag)

    for i in range(MAX_DIGEST_ITEMS + 5):
        vulnerability = _make_vulnerability(f"CVE-2026-{i:04d}", priority_score=float(i))
        _make_matched_product(vulnerability, tag)

    results = select_candidates_for_organization(org, window_start=WINDOW_START, window_end=WINDOW_END)

    assert len(results) == MAX_DIGEST_ITEMS


@pytest.mark.django_db
def test_out_of_window_vulnerabilities_are_excluded():
    tag = _make_tag()
    org = _make_org_with_tags(tag)

    stale = _make_vulnerability("CVE-2026-0001", priority_score="9.0", last_modified_at=OUT_OF_WINDOW)
    _make_matched_product(stale, tag)

    results = select_candidates_for_organization(org, window_start=WINDOW_START, window_end=WINDOW_END)

    assert results == []


@pytest.mark.django_db
def test_organization_without_user_returns_empty_list():
    org = Organization.objects.create(name="Ghost Org", slug="ghost-org")

    results = select_candidates_for_organization(org, window_start=WINDOW_START, window_end=WINDOW_END)

    assert results == []


@pytest.mark.django_db
def test_unmatched_products_do_not_count_as_direct_matches():
    tag = _make_tag()
    org = _make_org_with_tags(tag)

    vulnerability = _make_vulnerability("CVE-2026-0001", priority_score="9.0")
    VulnerabilityProduct.objects.create(
        vulnerability=vulnerability,
        raw_vendor="apache",
        raw_product="http server",
        normalized_vendor="apache",
        normalized_product="http server",
        match_status=VulnerabilityProductStatus.UNMATCHED,
    )

    results = select_candidates_for_organization(org, window_start=WINDOW_START, window_end=WINDOW_END)

    # falls back to backfill since there's no direct match, but it's still eligible
    assert len(results) == 1
    assert results[0].is_backfill is True
