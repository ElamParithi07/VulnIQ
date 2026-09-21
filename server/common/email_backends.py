from __future__ import annotations

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from digests.clients.resend import ResendClient, ResendClientError


class ResendHTTPEmailBackend(BaseEmailBackend):
    """Django email backend that sends via Resend's HTTPS API.

    Exists because outbound SMTP (port 587/25) is blocked on Render's free
    tier, so django.core.mail.backends.smtp cannot be used there — HTTPS is
    not blocked, and this reuses the same Resend client already used for
    digest delivery.
    """

    def __init__(self, *args, fail_silently: bool = False, client: ResendClient | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_silently = fail_silently
        self.client = client or ResendClient(api_key=settings.RESEND_API_KEY)

    def send_messages(self, email_messages) -> int:
        if not email_messages:
            return 0

        sent = 0
        for message in email_messages:
            html = self._extract_html(message)
            try:
                for recipient in message.to:
                    self.client.send_email(
                        from_email=message.from_email,
                        to=recipient,
                        subject=message.subject,
                        html=html or message.body,
                        text=message.body,
                    )
                sent += 1
            except ResendClientError:
                if not self.fail_silently:
                    raise
        return sent

    @staticmethod
    def _extract_html(message) -> str | None:
        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                return content
        return None
