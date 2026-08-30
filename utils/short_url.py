"""Optional URL shortening for share links (is.gd — no API key required)."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


def shorten_url(url: str, *, timeout: float = 10.0) -> str:
    """Return a shorter alias for *url*, or *url* unchanged if shortening fails."""
    if not url:
        return url
    try:
        response = requests.get(
            "https://is.gd/create.php",
            params={"format": "json", "url": url},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        short = (data.get("shorturl") or "").strip()
        if short:
            return short
        if data.get("errormessage"):
            logger.warning("is.gd: %s", data["errormessage"])
    except Exception as exc:
        logger.warning("URL shortening failed: %s", exc)
    return url
