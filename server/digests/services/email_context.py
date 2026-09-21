from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.urls import reverse

from digests.models import DailyDigest, DailyDigestItem

HIGH_EPSS_THRESHOLD = Decimal("0.7")
CRITICAL_CVSS_THRESHOLD = Decimal("9.0")


def _vendor_product_line(item: DailyDigestItem) -> str:
    if item.vendor_name and item.product_name:
        return f"{item.vendor_name.title()} {item.product_name.title()}"
    return (item.product_name or item.vendor_name or "").title()


def _chips(item: DailyDigestItem) -> list[str]:
    chips = []
    if item.is_kev:
        chips.append("Actively Exploited")
    if item.epss_probability is not None and item.epss_probability >= HIGH_EPSS_THRESHOLD:
        chips.append("High EPSS")
    if item.cvss_base_score is not None and item.cvss_base_score >= CRITICAL_CVSS_THRESHOLD:
        chips.append("Critical")
    return chips


def _item_context(item: DailyDigestItem) -> dict[str, Any]:
    return {
        "rank": item.rank,
        "title": item.title or item.cve_id,
        "cve_id": item.cve_id,
        "vendor_product_line": _vendor_product_line(item),
        "chips": _chips(item),
        "cvss_score": item.cvss_base_score,
        "epss_score": item.epss_probability,
        "ai_summary": item.ai_summary,
        "ai_remediation": item.ai_remediation,
        "date_label": item.date_label or "Published",
        "nvd_url": f"https://nvd.nist.gov/vuln/detail/{item.cve_id}",
    }


def build_email_subject(digest: DailyDigest) -> str:
    subject = f"VulnIQ Daily Digest - {digest.digest_date:%B %d, %Y}"
    if digest.matching_vulnerability_count == 0 and digest.backfill_vulnerability_count > 0:
        subject += " (Top Global Threats)"
    return subject


def build_email_context(digest: DailyDigest) -> dict[str, Any]:
    items = list(digest.items.all())
    has_backfill = any(item.is_backfill for item in items)
    is_fully_backfill = bool(items) and all(item.is_backfill for item in items)

    return {
        "organization_name": digest.organization.name,
        "digest_date": digest.digest_date,
        "has_backfill": has_backfill,
        "is_fully_backfill": is_fully_backfill,
        "items": [_item_context(item) for item in items],
        "dashboard_url": reverse("dashboard-home"),
        "settings_url": reverse("dashboard-settings"),
    }
