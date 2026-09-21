import pytest
import requests

from ingestion.clients import EPSSClient, EPSSClientError
from ingestion.clients.epss import MAX_CVE_IDS_PER_REQUEST


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

    def get(self, url, *, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.response


def test_client_fetches_scores_for_requested_cve_ids():
    response = DummyResponse(
        {"data": [{"cve": "CVE-2026-0001", "epss": "0.93", "percentile": "0.99"}]}
    )
    session = DummySession(response)
    client = EPSSClient(base_url="https://example.test/epss", timeout_seconds=10, session=session)

    scores = client.fetch_scores(["CVE-2026-0001"])

    assert scores == [{"cve": "CVE-2026-0001", "epss": "0.93", "percentile": "0.99"}]
    assert session.calls == [
        {
            "url": "https://example.test/epss",
            "params": {"cve": "CVE-2026-0001"},
            "timeout": 10,
        }
    ]


def test_client_joins_multiple_cve_ids_with_commas():
    session = DummySession(DummyResponse({"data": []}))
    client = EPSSClient(session=session)

    client.fetch_scores(["CVE-2026-0001", "CVE-2026-0002"])

    assert session.calls[0]["params"] == {"cve": "CVE-2026-0001,CVE-2026-0002"}


def test_client_returns_empty_list_without_request_when_no_cve_ids_given():
    session = DummySession(DummyResponse({"data": []}))
    client = EPSSClient(session=session)

    scores = client.fetch_scores([])

    assert scores == []
    assert session.calls == []


def test_client_rejects_too_many_cve_ids():
    client = EPSSClient(session=DummySession(DummyResponse({"data": []})))
    too_many = [f"CVE-2026-{i:04d}" for i in range(MAX_CVE_IDS_PER_REQUEST + 1)]

    with pytest.raises(EPSSClientError, match="Cannot request more than"):
        client.fetch_scores(too_many)


def test_client_raises_on_http_error():
    client = EPSSClient(session=DummySession(DummyResponse({}, status_code=503)))

    with pytest.raises(EPSSClientError, match="FIRST EPSS API request failed"):
        client.fetch_scores(["CVE-2026-0001"])


def test_client_raises_when_data_list_is_missing():
    client = EPSSClient(session=DummySession(DummyResponse({"status": "OK"})))

    with pytest.raises(
        EPSSClientError,
        match="FIRST EPSS API response did not include a data list",
    ):
        client.fetch_scores(["CVE-2026-0001"])
