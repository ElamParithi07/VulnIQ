from decimal import Decimal

import pytest

from intel.models import Vulnerability
from intel.services.scoring import calculate_priority_score, recompute_priority_scores, score_vulnerability


def test_calculate_priority_score_full_formula():
    score = calculate_priority_score(cvss_score=Decimal("9.8"), epss_score=Decimal("0.93"), is_cisa_kev=True)

    # (9.8 * 0.4) + (0.93 * 3.0) + 3.0 = 3.92 + 2.79 + 3.0
    assert score == Decimal("9.710")


def test_calculate_priority_score_without_kev():
    score = calculate_priority_score(cvss_score=Decimal("7.0"), epss_score=Decimal("0.1"), is_cisa_kev=False)

    # (7.0 * 0.4) + (0.1 * 3.0) + 0 = 2.8 + 0.3
    assert score == Decimal("3.100")


def test_calculate_priority_score_missing_cvss_contributes_zero():
    score = calculate_priority_score(cvss_score=None, epss_score=Decimal("0.5"), is_cisa_kev=False)

    assert score == Decimal("1.500")


def test_calculate_priority_score_missing_epss_contributes_zero():
    score = calculate_priority_score(cvss_score=Decimal("5.0"), epss_score=None, is_cisa_kev=False)

    assert score == Decimal("2.000")


def test_calculate_priority_score_all_missing_but_kev_true():
    score = calculate_priority_score(cvss_score=None, epss_score=None, is_cisa_kev=True)

    assert score == Decimal("3.000")


@pytest.mark.django_db
def test_score_vulnerability_persists_priority_score():
    vulnerability = Vulnerability.objects.create(
        cve_id="CVE-2026-0001",
        cvss_score=Decimal("9.0"),
        epss_score=Decimal("0.5"),
        is_cisa_kev=True,
    )

    score_vulnerability(vulnerability)
    vulnerability.refresh_from_db()

    assert vulnerability.priority_score == Decimal("8.100")


@pytest.mark.django_db
def test_recompute_priority_scores_updates_only_requested_cves():
    scored = Vulnerability.objects.create(cve_id="CVE-2026-0001", cvss_score=Decimal("8.0"))
    untouched = Vulnerability.objects.create(cve_id="CVE-2026-0002", cvss_score=Decimal("8.0"))

    updated_count = recompute_priority_scores(["CVE-2026-0001"])

    scored.refresh_from_db()
    untouched.refresh_from_db()

    assert updated_count == 1
    assert scored.priority_score == Decimal("3.200")
    assert untouched.priority_score is None
