from django.core.mail import EmailMultiAlternatives

from common.email_backends import ResendHTTPEmailBackend
from digests.clients.resend import ResendClientError


class StubResendClient:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def send_email(self, *, from_email, to, subject, html, text):
        self.calls.append({"from_email": from_email, "to": to, "subject": subject, "html": html, "text": text})
        if self.error:
            raise self.error
        return "stub-id"


def test_send_messages_uses_html_alternative_when_present():
    client = StubResendClient()
    backend = ResendHTTPEmailBackend(client=client)
    message = EmailMultiAlternatives(
        subject="Subject", body="Plain text body", from_email="a@vulniq.local", to=["b@example.test"]
    )
    message.attach_alternative("<p>HTML body</p>", "text/html")

    sent = backend.send_messages([message])

    assert sent == 1
    assert client.calls == [
        {
            "from_email": "a@vulniq.local",
            "to": "b@example.test",
            "subject": "Subject",
            "html": "<p>HTML body</p>",
            "text": "Plain text body",
        }
    ]


def test_send_messages_falls_back_to_plain_body_when_no_html():
    client = StubResendClient()
    backend = ResendHTTPEmailBackend(client=client)
    message = EmailMultiAlternatives(
        subject="Subject", body="Plain text only", from_email="a@vulniq.local", to=["b@example.test"]
    )

    backend.send_messages([message])

    assert client.calls[0]["html"] == "Plain text only"


def test_send_messages_sends_to_each_recipient():
    client = StubResendClient()
    backend = ResendHTTPEmailBackend(client=client)
    message = EmailMultiAlternatives(
        subject="Subject", body="Body", from_email="a@vulniq.local", to=["b@example.test", "c@example.test"]
    )

    sent = backend.send_messages([message])

    assert sent == 1
    assert [c["to"] for c in client.calls] == ["b@example.test", "c@example.test"]


def test_send_messages_returns_zero_for_empty_list():
    backend = ResendHTTPEmailBackend(client=StubResendClient())

    assert backend.send_messages([]) == 0


def test_send_messages_raises_on_failure_when_not_fail_silently():
    backend = ResendHTTPEmailBackend(client=StubResendClient(error=ResendClientError("down")))
    message = EmailMultiAlternatives(
        subject="Subject", body="Body", from_email="a@vulniq.local", to=["b@example.test"]
    )

    try:
        backend.send_messages([message])
        assert False, "expected ResendClientError"
    except ResendClientError:
        pass


def test_send_messages_swallows_failure_when_fail_silently():
    backend = ResendHTTPEmailBackend(client=StubResendClient(error=ResendClientError("down")), fail_silently=True)
    message = EmailMultiAlternatives(
        subject="Subject", body="Body", from_email="a@vulniq.local", to=["b@example.test"]
    )

    sent = backend.send_messages([message])

    assert sent == 0
