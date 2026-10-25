"""Single entry point for Garmin data access (Personal API default, legacy optional)."""

from __future__ import annotations

import logging
import os
from typing import Any

from utils.pipeline.garmin_personal_api import GarminPersonalAPI

logger = logging.getLogger(__name__)

# personal_api (default) | legacy (garminconnect + GARMINTOKENS / password)
GARMIN_SOURCE = os.getenv("GARMIN_SOURCE", "personal_api").strip().lower()


def is_legacy_client(client: Any) -> bool:
    return GARMIN_SOURCE == "legacy" or not isinstance(client, GarminPersonalAPI)


def is_personal_client(client: Any) -> bool:
    return isinstance(client, GarminPersonalAPI)


def get_garmin_client() -> Any | None:
    """Return a connected Garmin client, or None on failure."""
    if GARMIN_SOURCE == "legacy":
        # OLD WAY — kept for rollback if the official API changes.
        import utils.pipeline.garmin_cookies as garmin_cookies

        logger.info("Garmin source: legacy (garminconnect)")
        return garmin_cookies.main()

    logger.info("Garmin source: personal_api (official Personal API key)")
    try:
        return GarminPersonalAPI()
    except Exception as exc:  # noqa: BLE001
        logger.error("Personal API client failed: %s", exc)
        return None
