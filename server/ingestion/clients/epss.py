from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_EPSS_BASE_URL = "https://api.first.org/data/v1/epss"
DEFAULT_TIMEOUT_SECONDS = 30
MAX_CVE_IDS_PER_REQUEST = 100


class EPSSClientError(Exception):
    """Raised when the FIRST EPSS API request fails or returns invalid data."""


@dataclass(slots=True)
class EPSSClient:
    base_url: str = DEFAULT_EPSS_BASE_URL
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    session: requests.Session | None = None

    def fetch_scores(self, cve_ids: list[str]) -> list[dict[str, Any]]:
        if not cve_ids:
            return []

        if len(cve_ids) > MAX_CVE_IDS_PER_REQUEST:
            raise EPSSClientError(
                f"Cannot request more than {MAX_CVE_IDS_PER_REQUEST} CVE ids in a single EPSS request"
            )

        response = self._session.get(
            self.base_url,
            params={"cve": ",".join(cve_ids)},
            timeout=self.timeout_seconds,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise EPSSClientError("FIRST EPSS API request failed") from exc

        payload = response.json()
        scores = payload.get("data")

        if not isinstance(scores, list):
            raise EPSSClientError("FIRST EPSS API response did not include a data list")

        return scores

    @property
    def _session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()

        return self.session
