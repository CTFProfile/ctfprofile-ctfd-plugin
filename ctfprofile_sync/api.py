"""
HTTP client for the CTFProfile event sync API.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class CTFProfileClient:
    """Thin wrapper around the CTFProfile ctfd-sync REST endpoint."""

    def __init__(self, base_url: str, api_key: str, event_slug: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.event_slug = event_slug

    @property
    def sync_url(self) -> str:
        return f"{self.base_url}/api/events/{self.event_slug}/ctfd-sync/"

    def sync(self, payload: dict) -> dict:
        """
        POST *payload* to the sync endpoint.

        Returns the parsed JSON response dict on success.
        Raises :class:`CTFProfileAPIError` on HTTP or network errors.
        """
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.sync_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-CTFProfile-API-Key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise CTFProfileAPIError(
                f"HTTP {exc.code} from CTFProfile sync endpoint: {body_text[:200]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise CTFProfileAPIError(f"Network error: {exc.reason}") from exc

    def test(self) -> dict:
        """Send a minimal ping payload to verify connectivity and credentials."""
        return self.sync({"challenges": [], "users": [], "teams": [], "solves": [], "standings": []})


class CTFProfileAPIError(Exception):
    """Raised when the CTFProfile API returns an error."""
