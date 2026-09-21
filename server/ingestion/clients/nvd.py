from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests


DEFAULT_NVD_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEFAULT_RESULTS_PER_PAGE = 2000
DEFAULT_TIMEOUT_SECONDS = 30


class NVDClientError(Exception):
    """Raised when the NVD API request fails or returns invalid data."""


@dataclass(slots=True)
class NVDClient:
    base_url: str = DEFAULT_NVD_BASE_URL
    api_key: str | None = None
    results_per_page: int = DEFAULT_RESULTS_PER_PAGE
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    session: requests.Session | None = None

    def fetch_modified_between(
        self,
        *,
        start: datetime,
        end: datetime,
        start_index: int = 0,
    ) -> list[dict[str, Any]]:
        response = self._session.get(
            self.base_url,
            params={
                "lastModStartDate": start.isoformat(),
                "lastModEndDate": end.isoformat(),
                "resultsPerPage": self.results_per_page,
                "startIndex": start_index,
            },
            headers=self._headers,
            timeout=self.timeout_seconds,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise NVDClientError("NVD API request failed") from exc

        payload = response.json()
        vulnerabilities = payload.get("vulnerabilities")

        if not isinstance(vulnerabilities, list):
            raise NVDClientError("NVD API response did not include a vulnerabilities list")

        return vulnerabilities

    @property
    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}

        return {"apiKey": self.api_key}

    @property
    def _session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()

        return self.session
