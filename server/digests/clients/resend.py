from __future__ import annotations

from dataclasses import dataclass

import requests

DEFAULT_RESEND_BASE_URL = "https://api.resend.com/emails"
DEFAULT_TIMEOUT_SECONDS = 30


class ResendClientError(Exception):
    """Raised when the Resend API request fails or returns unusable data."""


@dataclass(slots=True)
class ResendClient:
    api_key: str
    base_url: str = DEFAULT_RESEND_BASE_URL
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    session: requests.Session | None = None

    def send_email(self, *, from_email: str, to: str, subject: str, html: str, text: str) -> str:
        """Send one email. Returns the provider message id.

        Resend accepting the request is treated as "sent" for MVP — no
        webhook-based delivery confirmation is integrated.
        """
        if not self.api_key:
            raise ResendClientError("Resend API key is not configured")

        response = self._session.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "from": from_email,
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text,
            },
            timeout=self.timeout_seconds,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise ResendClientError(
                f"Resend API request failed (HTTP {response.status_code}): {response.text[:300]}"
            ) from exc

        payload = response.json()
        message_id = payload.get("id")

        if not message_id:
            raise ResendClientError("Resend API response did not include a message id")

        return message_id

    @property
    def _session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()

        return self.session
