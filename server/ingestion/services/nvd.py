from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ingestion.clients import NVDClient


def fetch_recent_nvd_vulnerabilities(
    client: NVDClient | None = None,
    *,
    now: datetime | None = None,
    lookback: timedelta = timedelta(hours=24),
) -> list[dict[str, Any]]:
    active_client = client or NVDClient()
    end = now or datetime.now().astimezone()
    start = end - lookback

    return active_client.fetch_modified_between(start=start, end=end)
