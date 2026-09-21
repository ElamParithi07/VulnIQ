from __future__ import annotations

from datetime import UTC
from typing import Any

from django.utils import timezone as dj_timezone
from django.utils.dateparse import parse_datetime

from intel.models import VulnerabilityStatus


class SourceParsingError(Exception):
    """Raised when a raw source payload entry cannot be parsed."""


def _parse_datetime(value: str | None):
    if not value:
        return None

    parsed = parse_datetime(value)
    if parsed is None:
        return None

    if dj_timezone.is_naive(parsed):
        parsed = dj_timezone.make_aware(parsed, UTC)

    return parsed


def _map_nvd_status(value: str | None) -> str:
    if not value:
        return VulnerabilityStatus.UNKNOWN

    normalized = value.strip().lower()
    if normalized == "rejected":
        return VulnerabilityStatus.REJECTED
    if normalized == "modified":
        return VulnerabilityStatus.MODIFIED

    return VulnerabilityStatus.PUBLISHED


def _extract_cvss_score(metrics: dict[str, Any]) -> float | None:
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key) or []
        if not entries:
            continue
        score = entries[0].get("cvssData", {}).get("baseScore")
        if score is not None:
            return score

    return None


def _extract_cpe_list(configurations: list[dict[str, Any]]) -> list[str]:
    cpes: list[str] = []
    for config in configurations:
        for node in config.get("nodes", []):
            for cpe_match in node.get("cpeMatch", []):
                if cpe_match.get("vulnerable") and cpe_match.get("criteria"):
                    cpes.append(cpe_match["criteria"])

    return cpes


def parse_nvd_entry(entry: dict[str, Any]) -> dict[str, Any]:
    cve = entry.get("cve") or {}
    cve_id = cve.get("id")

    if not cve_id:
        raise SourceParsingError("NVD entry missing cve.id")

    descriptions = cve.get("descriptions") or []
    description = next(
        (d.get("value", "") for d in descriptions if d.get("lang") == "en"),
        "",
    )

    return {
        "cve_id": cve_id,
        "title": description[:500],
        "description": description,
        "status": _map_nvd_status(cve.get("vulnStatus")),
        "cvss_score": _extract_cvss_score(cve.get("metrics") or {}),
        "published_at": _parse_datetime(cve.get("published")),
        "last_modified_at": _parse_datetime(cve.get("lastModified")),
        "cpe_list": _extract_cpe_list(cve.get("configurations") or []),
        "raw_json": entry,
    }


def parse_kev_entry(entry: dict[str, Any]) -> dict[str, Any]:
    cve_id = entry.get("cveID")

    if not cve_id:
        raise SourceParsingError("KEV entry missing cveID")

    return {"cve_id": cve_id, "raw_json": entry}


def parse_epss_entry(entry: dict[str, Any]) -> dict[str, Any]:
    cve_id = entry.get("cve")

    if not cve_id:
        raise SourceParsingError("EPSS entry missing cve")

    raw_score = entry.get("epss")
    try:
        epss_score = float(raw_score) if raw_score is not None else None
    except (TypeError, ValueError):
        epss_score = None

    return {"cve_id": cve_id, "epss_score": epss_score, "raw_json": entry}
