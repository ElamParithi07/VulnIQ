from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from intel.models import Vulnerability

CVSS_WEIGHT = Decimal("0.4")
EPSS_WEIGHT = Decimal("3.0")  # EPSS probability * 10 * 0.3
KEV_WEIGHT = Decimal("3.0")


def calculate_priority_score(
    *,
    cvss_score: Decimal | float | None,
    epss_score: Decimal | float | None,
    is_cisa_kev: bool,
) -> Decimal:
    """Priority Score = (CVSS * 0.4) + (EPSS * 10 * 0.3) + (KEV ? 3.0 : 0).

    Missing CVSS/EPSS contribute zero to their term rather than blocking
    the score, so partially-enriched vulnerabilities still rank.
    """
    cvss_component = Decimal(str(cvss_score)) * CVSS_WEIGHT if cvss_score is not None else Decimal(0)
    epss_component = Decimal(str(epss_score)) * EPSS_WEIGHT if epss_score is not None else Decimal(0)
    kev_component = KEV_WEIGHT if is_cisa_kev else Decimal(0)

    return (cvss_component + epss_component + kev_component).quantize(Decimal("0.001"))


def score_vulnerability(vulnerability: Vulnerability) -> Vulnerability:
    vulnerability.priority_score = calculate_priority_score(
        cvss_score=vulnerability.cvss_score,
        epss_score=vulnerability.epss_score,
        is_cisa_kev=vulnerability.is_cisa_kev,
    )
    vulnerability.save(update_fields=["priority_score", "updated_at"])
    return vulnerability


def recompute_priority_scores(cve_ids: Iterable[str]) -> int:
    updated = 0
    for vulnerability in Vulnerability.objects.filter(cve_id__in=list(cve_ids)):
        score_vulnerability(vulnerability)
        updated += 1
    return updated
