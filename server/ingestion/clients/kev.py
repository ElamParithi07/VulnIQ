from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_KEV_BASE_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
DEFAULT_TIMEOUT_SECONDS = 30


class KEVClientError(Exception):
    """Raised when the CISA KEV feed request fails or returns invalid data."""


@dataclass(slots=True)
class KEVClient:
    base_url: str = DEFAULT_KEV_BASE_URL
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    session: requests.Session | None = None

    def fetch_catalog(self) -> list[dict[str, Any]]:
        response = self._session.get(self.base_url, timeout=self.timeout_seconds)

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise KEVClientError("CISA KEV feed request failed") from exc

        payload = response.json()
        vulnerabilities = payload.get("vulnerabilities")

        if not isinstance(vulnerabilities, list):
            raise KEVClientError("CISA KEV feed response did not include a vulnerabilities list")

        return vulnerabilities

    @property
    def _session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()

        return self.session
