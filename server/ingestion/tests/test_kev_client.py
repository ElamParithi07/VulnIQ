import pytest
import requests

from ingestion.clients import KEVClient, KEVClientError


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

    def get(self, url, *, timeout):
        self.calls.append({"url": url, "timeout": timeout})
        return self.response


def test_client_fetches_catalog_vulnerabilities():
    response = DummyResponse(
        {
            "title": "CISA KEV Catalog",
            "vulnerabilities": [{"cveID": "CVE-2026-0001", "vendorProject": "Microsoft"}],
        }
    )
    session = DummySession(response)
    client = KEVClient(base_url="https://example.test/kev", timeout_seconds=10, session=session)

    vulnerabilities = client.fetch_catalog()

    assert vulnerabilities == [{"cveID": "CVE-2026-0001", "vendorProject": "Microsoft"}]
    assert session.calls == [{"url": "https://example.test/kev", "timeout": 10}]


def test_client_raises_on_http_error():
    client = KEVClient(session=DummySession(DummyResponse({}, status_code=503)))

    with pytest.raises(KEVClientError, match="CISA KEV feed request failed"):
        client.fetch_catalog()


def test_client_raises_when_vulnerabilities_list_is_missing():
    client = KEVClient(session=DummySession(DummyResponse({"title": "no data"})))

    with pytest.raises(
        KEVClientError,
        match="CISA KEV feed response did not include a vulnerabilities list",
    ):
        client.fetch_catalog()
