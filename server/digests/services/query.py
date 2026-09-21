from __future__ import annotations

from accounts.models import Organization
from digests.models import DailyDigest


def get_latest_digest(organization: Organization) -> DailyDigest | None:
    return (
        DailyDigest.objects.filter(organization=organization)
        .prefetch_related("items")
        .order_by("-digest_date", "-created_at")
        .first()
    )
