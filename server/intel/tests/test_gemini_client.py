import pytest
import requests

from intel.clients.gemini import GeminiClient, GeminiClientError


class DummyResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload

    @property
    def text(self):
        return str(self._payload)


class DummySession:
    def __init__(self, response: DummyResponse):
        self.response = response
        self.calls = []

    def post(self, url, *, params, json, timeout):
        self.calls.append({"url": url, "params": params, "json": json, "timeout": timeout})
        return self.response


def test_generate_text_returns_first_candidate_text():
    response = DummyResponse(
        {"candidates": [{"content": {"parts": [{"text": "SUMMARY: hi\nREMEDIATION: patch it"}]}}]}
    )
    session = DummySession(response)
    client = GeminiClient(api_key="secret", model_name="gemini-2.5-flash", session=session)

    text = client.generate_text("some prompt")

    assert text == "SUMMARY: hi\nREMEDIATION: patch it"
    assert session.calls == [
        {
            "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            "params": {"key": "secret"},
            "json": {"contents": [{"parts": [{"text": "some prompt"}]}]},
            "timeout": 30,
        }
    ]


def test_generate_text_raises_when_api_key_missing():
    client = GeminiClient(api_key="", session=DummySession(DummyResponse({})))

    with pytest.raises(GeminiClientError, match="API key is not configured"):
        client.generate_text("prompt")


def test_generate_text_raises_on_http_error():
    client = GeminiClient(api_key="secret", session=DummySession(DummyResponse({}, status_code=503)))

    with pytest.raises(GeminiClientError, match="Gemini API request failed"):
        client.generate_text("prompt")


def test_generate_text_raises_when_response_shape_is_unexpected():
    client = GeminiClient(api_key="secret", session=DummySession(DummyResponse({"candidates": []})))

    with pytest.raises(GeminiClientError, match="did not include usable text"):
        client.generate_text("prompt")
