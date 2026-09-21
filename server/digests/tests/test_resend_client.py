import pytest
import requests

from digests.clients.resend import ResendClient, ResendClientError


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

    def post(self, url, *, headers, json, timeout):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return self.response


def test_send_email_returns_provider_message_id():
    response = DummyResponse({"id": "msg-123"})
    session = DummySession(response)
    client = ResendClient(api_key="secret", session=session)

    message_id = client.send_email(
        from_email="alerts@vulniq.local",
        to="owner@acme.test",
        subject="Subject",
        html="<p>hi</p>",
        text="hi",
    )

    assert message_id == "msg-123"
    assert session.calls == [
        {
            "url": "https://api.resend.com/emails",
            "headers": {"Authorization": "Bearer secret"},
            "json": {
                "from": "alerts@vulniq.local",
                "to": ["owner@acme.test"],
                "subject": "Subject",
                "html": "<p>hi</p>",
                "text": "hi",
            },
            "timeout": 30,
        }
    ]


def test_send_email_raises_when_api_key_missing():
    client = ResendClient(api_key="", session=DummySession(DummyResponse({})))

    with pytest.raises(ResendClientError, match="API key is not configured"):
        client.send_email(from_email="a@b.com", to="c@d.com", subject="s", html="h", text="t")


def test_send_email_raises_on_http_error():
    client = ResendClient(api_key="secret", session=DummySession(DummyResponse({}, status_code=422)))

    with pytest.raises(ResendClientError, match="Resend API request failed"):
        client.send_email(from_email="a@b.com", to="c@d.com", subject="s", html="h", text="t")


def test_send_email_raises_when_message_id_missing():
    client = ResendClient(api_key="secret", session=DummySession(DummyResponse({"status": "ok"})))

    with pytest.raises(ResendClientError, match="did not include a message id"):
        client.send_email(from_email="a@b.com", to="c@d.com", subject="s", html="h", text="t")
