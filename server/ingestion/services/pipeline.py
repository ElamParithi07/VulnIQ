from __future__ import annotations

import logging
from datetime import datetime, timedelta

from django.utils import timezone

from ingestion.clients import EPSSClient, EPSSClientError, KEVClient, KEVClientError, NVDClient, NVDClientError
from ingestion.clients.epss import MAX_CVE_IDS_PER_REQUEST
from ingestion.models import IngestionRun, IngestionRunStatus, IngestionRunType
from ingestion.services.runs import complete_run, mark_degraded, start_run
from ingestion.services.source_parsing import (
    SourceParsingError,
    parse_epss_entry,
    parse_kev_entry,
    parse_nvd_entry,
)
from ingestion.services.upserts import upsert_epss_score, upsert_kev_status, upsert_nvd_vulnerability
from intel.services.scoring import recompute_priority_scores

logger = logging.getLogger(__name__)


def run_ingestion_pipeline(
    *,
    run_type: str = IngestionRunType.SCHEDULED,
    nvd_client: NVDClient | None = None,
    kev_client: KEVClient | None = None,
    epss_client: EPSSClient | None = None,
    now: datetime | None = None,
    lookback: timedelta = timedelta(hours=24),
) -> IngestionRun:
    """Fetch NVD/KEV/EPSS, persist vulnerabilities, and record run outcome.

    Each source failure degrades the run instead of aborting it, so a
    down KEV or EPSS endpoint never blocks NVD ingestion for the day.
    KEV/EPSS annotate only vulnerabilities touched by this run's NVD
    pull; they do not fabricate vulnerability records on their own.
    """
    run = start_run(run_type=run_type)
    nvd_client = nvd_client or NVDClient()
    kev_client = kev_client or KEVClient()
    epss_client = epss_client or EPSSClient()

    end = now or timezone.now()
    start = end - lookback

    touched_cve_ids: list[str] = []

    try:
        raw_entries = nvd_client.fetch_modified_between(start=start, end=end)
    except NVDClientError as exc:
        mark_degraded(run, f"NVD fetch failed: {exc}")
        raw_entries = []

    for entry in raw_entries:
        try:
            parsed = parse_nvd_entry(entry)
        except SourceParsingError:
            logger.warning("Skipping malformed NVD entry", exc_info=True)
            continue

        upsert_nvd_vulnerability(parsed)
        touched_cve_ids.append(parsed["cve_id"])

    run.nvd_count = len(touched_cve_ids)

    try:
        kev_entries = kev_client.fetch_catalog()
    except KEVClientError as exc:
        mark_degraded(run, f"KEV fetch failed: {exc}")
        kev_entries = []

    touched_cve_id_set = set(touched_cve_ids)
    kev_matched = 0
    for entry in kev_entries:
        try:
            parsed = parse_kev_entry(entry)
        except SourceParsingError:
            continue

        if parsed["cve_id"] not in touched_cve_id_set:
            continue

        if upsert_kev_status(parsed) is not None:
            kev_matched += 1

    run.kev_count = kev_matched

    epss_matched = 0
    try:
        for chunk_start in range(0, len(touched_cve_ids), MAX_CVE_IDS_PER_REQUEST):
            chunk = touched_cve_ids[chunk_start : chunk_start + MAX_CVE_IDS_PER_REQUEST]
            for entry in epss_client.fetch_scores(chunk):
                try:
                    parsed = parse_epss_entry(entry)
                except SourceParsingError:
                    continue

                if upsert_epss_score(parsed) is not None:
                    epss_matched += 1
    except EPSSClientError as exc:
        mark_degraded(run, f"EPSS fetch failed: {exc}")

    run.epss_count = epss_matched
    run.save(update_fields=["nvd_count", "kev_count", "epss_count", "updated_at"])

    recompute_priority_scores(touched_cve_ids)

    complete_run(run, status=IngestionRunStatus.SUCCEEDED)
    return run
