from __future__ import annotations

import logging
from datetime import datetime, timedelta

from django.utils import timezone

from accounts.models import Organization
from digests.clients.resend import ResendClient
from digests.models import DailyDigest
from digests.services.delivery import send_digest
from digests.services.snapshots import build_daily_digest
from ingestion.clients import EPSSClient, KEVClient, NVDClient
from ingestion.models import IngestionRun, IngestionRunType
from ingestion.services.locking import acquire_pipeline_lock
from ingestion.services.pipeline import run_ingestion_pipeline
from intel.clients.gemini import GeminiClient
from intel.services.enrichment import generate_enrichment

logger = logging.getLogger(__name__)


def _eligible_organizations():
    """Orgs with digest_enabled=True, a user, and a verified user email."""
    return Organization.objects.filter(
        digest_enabled=True,
        user__isnull=False,
        user__is_email_verified=True,
    )


def _ensure_enrichment_for_digest(digest: DailyDigest, *, gemini_client: GeminiClient | None) -> None:
    for item in digest.items.select_related("vulnerability").all():
        enrichment = generate_enrichment(
            item.vulnerability,
            vendor=item.vendor_name,
            product=item.product_name,
            client=gemini_client,
        )
        if item.ai_summary != enrichment.summary_text or item.ai_remediation != enrichment.remediation_text:
            item.ai_summary = enrichment.summary_text
            item.ai_remediation = enrichment.remediation_text
            item.save(update_fields=["ai_summary", "ai_remediation", "updated_at"])


def run_daily_digest_pipeline(
    *,
    run_type: str = IngestionRunType.SCHEDULED,
    now: datetime | None = None,
    nvd_client: NVDClient | None = None,
    kev_client: KEVClient | None = None,
    epss_client: EPSSClient | None = None,
    gemini_client: GeminiClient | None = None,
    resend_client: ResendClient | None = None,
) -> IngestionRun:
    """Canonical daily pipeline entrypoint.

    Ingests NVD/KEV/EPSS, then for each eligible organization builds (or
    reuses) the immutable digest snapshot, ensures AI enrichment for its
    items, and sends it. Protected end-to-end by a DB-backed lock so the
    scheduler, CLI, and admin "run now" trigger can never overlap. One
    organization's failure does not stop the others; it is logged and
    skipped, matching the documented failure/retry rules.

    Sending is skipped when the org's digest for the day is already SENT,
    so re-running this same-day (e.g. a manual admin re-trigger) never
    silently re-emails a customer. Explicit resends are the admin's
    dedicated "resend digest" action, not an automatic side effect of
    re-running the daily pipeline.

    The optional *_client overrides exist so tests (and any future
    alternate entrypoints) can inject stubs instead of hitting live
    NVD/KEV/EPSS/Gemini/Resend services; production callers should omit
    them and let each service default to its configured client.
    """
    with acquire_pipeline_lock():
        current_time = now or timezone.now()
        run = run_ingestion_pipeline(
            run_type=run_type,
            now=current_time,
            nvd_client=nvd_client,
            kev_client=kev_client,
            epss_client=epss_client,
        )

        window_end = current_time
        window_start = window_end - timedelta(hours=24)
        digest_date = current_time.date()

        candidate_count = 0
        digest_count = 0

        for organization in _eligible_organizations():
            try:
                digest = build_daily_digest(
                    organization,
                    digest_date=digest_date,
                    window_start=window_start,
                    window_end=window_end,
                )
                if digest is None:
                    continue

                candidate_count += digest.items.count()
                _ensure_enrichment_for_digest(digest, gemini_client=gemini_client)
                if digest.status != DailyDigest.Status.SENT:
                    send_digest(digest, client=resend_client)
                digest_count += 1
            except Exception:
                logger.exception(
                    "Daily digest generation failed for organization %s; continuing with others",
                    organization.pk,
                )
                continue

        run.candidate_count = candidate_count
        run.digest_count = digest_count
        run.save(update_fields=["candidate_count", "digest_count", "updated_at"])

        return run
