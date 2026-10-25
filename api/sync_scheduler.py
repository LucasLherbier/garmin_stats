"""In-app Garmin sync: auto-refresh on API startup + optional manual trigger.

Disable startup sync: GARMIN_SYNC_ON_STARTUP=off
Disable all in-app sync: GARMIN_SYNC_ENABLED=false

If GitHub Actions cron still runs the same pipeline, disable one path to avoid
double sync (see .github/workflows/data_extraction_automate.yml).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

SYNC_ENABLED = os.getenv("GARMIN_SYNC_ENABLED", "true").lower() == "true"
SYNC_ON_STARTUP = os.getenv("GARMIN_SYNC_ON_STARTUP", "on").lower() != "off"
STARTUP_MAX_AGE_HOURS = float(os.getenv("GARMIN_SYNC_STARTUP_MAX_AGE_HOURS", "12"))
_LAST_SYNC_GCS_PATH = "sync_state/last_sync.json"

_run_lock = threading.Lock()
_last_run: dict = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "detail": None,
}


def _read_last_success() -> datetime | None:
    try:
        from utils.utils_gcp import bucket

        blob = bucket.blob(_LAST_SYNC_GCS_PATH)
        if blob.exists():
            data = json.loads(blob.download_as_text())
            return datetime.fromisoformat(data["finished_at"])
    except Exception:  # noqa: BLE001
        logger.debug("Could not read last-sync state from GCS.", exc_info=True)
    return None


def _write_last_success(when: datetime) -> None:
    try:
        from utils.utils_gcp import bucket

        blob = bucket.blob(_LAST_SYNC_GCS_PATH)
        blob.upload_from_string(
            json.dumps({"finished_at": when.isoformat()}),
            content_type="application/json",
        )
    except Exception:  # noqa: BLE001
        logger.debug("Could not persist last-sync state to GCS.", exc_info=True)


def get_last_run_status() -> dict:
    return dict(_last_run)


def _execute_sync(manual: bool) -> dict:
    from utils.pipeline.run_garmin_sync import run_garmin_sync, sync_start_date

    if not SYNC_ENABLED:
        detail = "sync disabled (GARMIN_SYNC_ENABLED=false)"
        _last_run.update(status="skipped", detail=detail)
        return {"status": "skipped", "detail": detail}

    started = datetime.now(timezone.utc)
    _last_run.update(
        status="running",
        started_at=started.isoformat(),
        finished_at=None,
        detail="manual" if manual else "startup",
    )
    try:
        run_garmin_sync(sync_start_date())
        finished = datetime.now(timezone.utc)
        _last_run.update(status="success", finished_at=finished.isoformat(), detail="ok")
        _write_last_success(finished)
        return {"status": "success", "detail": "ok"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Garmin sync failed")
        finished = datetime.now(timezone.utc)
        _last_run.update(
            status="failed",
            finished_at=finished.isoformat(),
            detail=str(exc),
        )
        return {"status": "failed", "detail": str(exc)}


def run_scheduled_sync(manual: bool = False) -> dict:
    """Run the full sync pipeline (blocking)."""
    with _run_lock:
        return _execute_sync(manual)


def _background_sync(manual: bool) -> None:
    try:
        _execute_sync(manual=manual)
    finally:
        _run_lock.release()


def trigger_background_sync(*, manual: bool = False) -> dict:
    """Start sync in a background thread (non-blocking for HTTP handlers)."""
    if not SYNC_ENABLED:
        return {"status": "skipped", "detail": "sync disabled"}

    if not _run_lock.acquire(blocking=False):
        return {"status": "busy", "detail": "sync already running"}

    _last_run.update(status="queued", detail="manual" if manual else "startup")
    threading.Thread(target=_background_sync, args=(manual,), daemon=True).start()
    return {"status": "started", "detail": "sync running in background"}


def trigger_manual_sync() -> dict:
    return trigger_background_sync(manual=True)


def maybe_sync_on_startup() -> None:
    if not SYNC_ENABLED or not SYNC_ON_STARTUP:
        return
    last = _read_last_success()
    if last is not None:
        age = datetime.now(timezone.utc) - last
        if age < timedelta(hours=STARTUP_MAX_AGE_HOURS):
            logger.info(
                "Startup sync skipped: last success %s ago (< %sh).",
                age,
                STARTUP_MAX_AGE_HOURS,
            )
            return
    logger.info("Startup sync: data stale or unknown — kicking off a refresh.")
    trigger_background_sync(manual=False)


def start_scheduler() -> None:
    maybe_sync_on_startup()


def stop_scheduler() -> None:
    pass
