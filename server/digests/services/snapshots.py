from __future__ import annotations

from datetime import date, datetime

from django.db import transaction
from django.utils import timezone

from accounts.models import Organization
from digests.models import DailyDigest, DailyDigestItem
from digests.services.selection import select_candidates_for_organization
from intel.models import Vulnerability, VulnerabilityAIEnrichment


def _latest_enrichment(vulnerability: Vulnerability) -> VulnerabilityAIEnrichment | None:
    try:
        return vulnerability.latest_enrichment
    except VulnerabilityAIEnrichment.DoesNotExist:
        return None


def _date_label(vulnerability: Vulnerability, window_start: datetime) -> str:
    """"Published" if first published in this window, else "Updated" if it
    reappeared due to a modification in this window, else "Published" as the
    deterministic default when timing data is missing."""
    if vulnerability.published_at is not None and vulnerability.published_at >= window_start:
        return "Published"
    if vulnerability.last_modified_at is not None and vulnerability.last_modified_at >= window_start:
        return "Updated"
    return "Published"


def build_daily_digest(
    organization: Organization,
    *,
    digest_date: date,
    window_start: datetime,
    window_end: datetime,
) -> DailyDigest | None:
    """Build and persist one immutable digest snapshot for an organization/day.

    Idempotent: if a digest already exists for (organization, digest_date) it
    is returned unchanged rather than regenerated, so reruns and retries
    never mutate a snapshot that may already have been emailed. Returns
    None when there is no eligible user or no candidates at all for the day
    (nothing worth sending).
    """
    existing = DailyDigest.objects.filter(organization=organization, digest_date=digest_date).first()
    if existing is not None:
        return existing

    user = getattr(organization, "user", None)
    if user is None:
        return None

    candidates = select_candidates_for_organization(
        organization,
        window_start=window_start,
        window_end=window_end,
    )
    if not candidates:
        return None

    with transaction.atomic():
        digest = DailyDigest.objects.create(
            organization=organization,
            user=user,
            digest_date=digest_date,
            generated_at=timezone.now(),
            status=DailyDigest.Status.READY,
            matching_vulnerability_count=sum(1 for c in candidates if not c.is_backfill),
            backfill_vulnerability_count=sum(1 for c in candidates if c.is_backfill),
        )

        for rank, candidate in enumerate(candidates, start=1):
            vulnerability = candidate.vulnerability
            enrichment = _latest_enrichment(vulnerability)
            DailyDigestItem.objects.create(
                daily_digest=digest,
                vulnerability=vulnerability,
                rank=rank,
                is_backfill=candidate.is_backfill,
                title=vulnerability.title,
                vendor_name=candidate.vendor_name,
                product_name=candidate.product_name,
                cve_id=vulnerability.cve_id,
                date_label=_date_label(vulnerability, window_start),
                severity_label=vulnerability.status,
                cvss_base_score=vulnerability.cvss_score,
                epss_probability=vulnerability.epss_score,
                is_kev=vulnerability.is_cisa_kev,
                ai_summary=enrichment.summary_text if enrichment else "",
                ai_remediation=enrichment.remediation_text if enrichment else "",
            )

    return digest
