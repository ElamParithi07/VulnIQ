from __future__ import annotations

from dataclasses import dataclass

import requests

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL_NAME = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 30


class GeminiClientError(Exception):
    """Raised when the Gemini API request fails or returns unusable data."""


@dataclass(slots=True)
class GeminiClient:
    api_key: str
    model_name: str = DEFAULT_MODEL_NAME
    base_url: str = DEFAULT_GEMINI_BASE_URL
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    session: requests.Session | None = None

    def generate_text(self, prompt: str) -> str:
        if not self.api_key:
            raise GeminiClientError("Gemini API key is not configured")

        url = f"{self.base_url}/{self.model_name}:generateContent"
        response = self._session.post(
            url,
            params={"key": self.api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=self.timeout_seconds,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise GeminiClientError(
                f"Gemini API request failed (HTTP {response.status_code}): {response.text[:300]}"
            ) from exc

        payload = response.json()

        try:
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiClientError("Gemini API response did not include usable text") from exc

    @property
    def _session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()

        return self.session
