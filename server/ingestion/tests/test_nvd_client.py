from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import requests

from ingestion.clients import NVDClient, NVDClientError
from ingestion.services import fetch_recent_nvd_vulnerabilities


class DummyResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class DummySession:
    def __init__(self, response: DummyResponse):
        self.response = response
        self.calls = []

    def get(self, url, *, params, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.response


def test_client_fetches_modified_vulnerabilities_with_expected_request_shape():
    start = datetime(2026, 8, 8, 0, 0, tzinfo=UTC)
    end = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
    response = DummyResponse({"vulnerabilities": [{"cve": {"id": "CVE-2026-0001"}}]})
    session = DummySession(response)
    client = NVDClient(
        base_url="https://example.test/nvd",
        api_key="secret-key",
        results_per_page=500,
        timeout_seconds=15,
        session=session,
    )

    vulnerabilities = client.fetch_modified_between(start=start, end=end, start_index=25)

    assert vulnerabilities == [{"cve": {"id": "CVE-2026-0001"}}]
    assert session.calls == [
        {
            "url": "https://example.test/nvd",
            "params": {
                "lastModStartDate": "2026-08-08T00:00:00+00:00",
                "lastModEndDate": "2026-08-09T00:00:00+00:00",
                "resultsPerPage": 500,
                "startIndex": 25,
            },
            "headers": {"apiKey": "secret-key"},
            "timeout": 15,
        }
    ]


def test_client_omits_api_key_header_when_not_configured():
    response = DummyResponse({"vulnerabilities": []})
    session = DummySession(response)
    client = NVDClient(session=session)

    client.fetch_modified_between(
        start=datetime(2026, 8, 8, 0, 0, tzinfo=UTC),
        end=datetime(2026, 8, 9, 0, 0, tzinfo=UTC),
    )

    assert session.calls[0]["headers"] == {}


def test_client_raises_on_http_error():
    client = NVDClient(session=DummySession(DummyResponse({}, status_code=503)))

    with pytest.raises(NVDClientError, match="NVD API request failed"):
        client.fetch_modified_between(
            start=datetime(2026, 8, 8, 0, 0, tzinfo=UTC),
            end=datetime(2026, 8, 9, 0, 0, tzinfo=UTC),
        )


def test_client_raises_when_vulnerabilities_list_is_missing():
    client = NVDClient(session=DummySession(DummyResponse({"results": []})))

    with pytest.raises(
        NVDClientError,
        match="NVD API response did not include a vulnerabilities list",
    ):
        client.fetch_modified_between(
            start=datetime(2026, 8, 8, 0, 0, tzinfo=UTC),
            end=datetime(2026, 8, 9, 0, 0, tzinfo=UTC),
        )


def test_service_fetches_last_24_hours_from_supplied_now():
    end = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)

    class RecordingClient:
        def __init__(self):
            self.calls = []

        def fetch_modified_between(self, *, start, end):
            self.calls.append({"start": start, "end": end})
            return [{"cve": {"id": "CVE-2026-0002"}}]

    client = RecordingClient()

    vulnerabilities = fetch_recent_nvd_vulnerabilities(client=client, now=end)

    assert vulnerabilities == [{"cve": {"id": "CVE-2026-0002"}}]
    assert client.calls == [
        {
            "start": end - timedelta(hours=24),
            "end": end,
        }
    ]
