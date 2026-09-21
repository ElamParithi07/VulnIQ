from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from accounts.models import Organization
from intel.models import Vulnerability, VulnerabilityProduct, VulnerabilityProductStatus, VulnerabilityStatus

MAX_DIGEST_ITEMS = 10

_ELIGIBLE_STATUSES = (VulnerabilityStatus.PUBLISHED, VulnerabilityStatus.MODIFIED)


@dataclass(slots=True)
class SelectedCandidate:
    vulnerability: Vulnerability
    is_backfill: bool
    vendor_name: str
    product_name: str


def select_candidates_for_organization(
    organization: Organization,
    *,
    window_start: datetime,
    window_end: datetime,
    limit: int = MAX_DIGEST_ITEMS,
) -> list[SelectedCandidate]:
    """Select up to `limit` digest candidates for one organization.

    Direct product-tag matches are ranked by priority_score first; if fewer
    than `limit` are found, the remainder is backfilled with the highest
    global-priority vulnerabilities from the same window. A CVE matching
    multiple selected tags is included only once (first/highest-ranked
    match wins for display).
    """
    direct_candidates: list[SelectedCandidate] = []
    seen_cve_ids: set[str] = set()

    user = getattr(organization, "user", None)
    if user is not None:
        tag_ids = list(user.selected_tech_tags.values_list("tag_id", flat=True))
        if tag_ids:
            products = (
                VulnerabilityProduct.objects.select_related("vulnerability")
                .filter(
                    tech_tag_id__in=tag_ids,
                    match_status=VulnerabilityProductStatus.MATCHED,
                    vulnerability__status__in=_ELIGIBLE_STATUSES,
                    vulnerability__last_modified_at__gte=window_start,
                    vulnerability__last_modified_at__lte=window_end,
                    vulnerability__priority_score__isnull=False,
                )
                .order_by("-vulnerability__priority_score", "vulnerability__cve_id")
            )
            for product in products:
                cve_id = product.vulnerability.cve_id
                if cve_id in seen_cve_ids:
                    continue
                seen_cve_ids.add(cve_id)
                direct_candidates.append(
                    SelectedCandidate(
                        vulnerability=product.vulnerability,
                        is_backfill=False,
                        vendor_name=product.normalized_vendor,
                        product_name=product.normalized_product,
                    )
                )
                if len(direct_candidates) >= limit:
                    break

    remaining = limit - len(direct_candidates)
    if remaining <= 0:
        return direct_candidates

    backfill_qs = (
        Vulnerability.objects.filter(
            status__in=_ELIGIBLE_STATUSES,
            last_modified_at__gte=window_start,
            last_modified_at__lte=window_end,
            priority_score__isnull=False,
        )
        .exclude(cve_id__in=seen_cve_ids)
        .order_by("-priority_score", "cve_id")
    )

    backfill_candidates: list[SelectedCandidate] = []
    for vulnerability in backfill_qs:
        if len(backfill_candidates) >= remaining:
            break
        backfill_candidates.append(
            SelectedCandidate(
                vulnerability=vulnerability,
                is_backfill=True,
                vendor_name="",
                product_name="",
            )
        )

    return direct_candidates + backfill_candidates
