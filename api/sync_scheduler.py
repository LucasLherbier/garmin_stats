"""In-app Garmin sync scheduler (Endurain-style direct sync, single user).

Replaces the GitHub Actions cron: an APScheduler BackgroundScheduler runs the
weekly sync inside the FastAPI process, reading/writing the encrypted token
vault in GCS instead of the GARMINTOKENS GitHub secret.

IMPORTANT: disable the `.github/workflows/data_extraction_automate.yml`
schedule once this has run successfully at least once — otherwise both the
cron and the scheduler will sync and double the Garmin API load (429 risk).
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger(__name__)

SYNC_ENABLED = os.getenv("GARMIN_SYNC_ENABLED", "true").lower() == "true"
# Weekly run: Monday 02:00 UTC (matches the old GitHub Actions cron).
SYNC_DAY_OF_WEEK = os.getenv("GARMIN_SYNC_DAY_OF_WEEK", "mon")
SYNC_HOUR_UTC = int(os.getenv("GARMIN_SYNC_HOUR_UTC", "2"))

_scheduler = None
_run_lock = threading.Lock()
_last_run: dict = {
    "status": "never_run",
    "started_at": None,
    "finished_at": None,
    "detail": None,
}


def _start_date_for_run() -> str:
    # Same window as the old GitHub workflow: 14 days ago (process_date_range
    # rewinds to the Monday of that week itself).
    return (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")


def run_scheduled_sync(manual: bool = False) -> dict:
    """Execute one sync run. Never raises; outcome recorded in _last_run."""
    from scripts.weekly_garmin_sync import run_weekly_sync
    from utils.pipeline import token_vault

    if not _run_lock.acquire(blocking=False):
        result = dict(_last_run)
        result["status"] = "already_running"
        return result
    _last_run.update(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        detail="manual trigger" if manual else "scheduled",
    )
    try:
        blob = token_vault.load_token_blob()
        if blob:
            logger.info("Sync login: GCS vault or GARMINTOKENS.")
        else:
            logger.info(
                "No vault/GARMINTOKENS; sync will use USER_EMAIL / local .garmin_tokens (CLI path)."
            )
        code, refreshed = run_weekly_sync(
            _start_date_for_run(), token_blob=blob if blob else None
        )
        if code != 0:
            raise RuntimeError(f"Sync failed with exit code {code}.")
        if refreshed and (not blob or refreshed.strip() != blob.strip()):
            detail = (
                "ok, vault updated"
                if token_vault.save_token_blob(refreshed)
                else "ok, vault write failed"
            )
        else:
            detail = "ok, tokens unchanged"
        _last_run.update(status="success", detail=detail)
    except Exception as exc:  # noqa: BLE001 - record any failure, never crash scheduler
        logger.exception("Scheduled Garmin sync failed")
        _last_run.update(status="failed", detail=str(exc))
    finally:
        _last_run["finished_at"] = datetime.now(timezone.utc).isoformat()
        _run_lock.release()
    return dict(_last_run)


def trigger_manual_sync() -> dict:
    """Start a sync in a background thread; returns immediately."""
    thread = threading.Thread(
        target=run_scheduled_sync, kwargs={"manual": True}, daemon=True
    )
    thread.start()
    return {"status": "started"}


def get_sync_status() -> dict:
    return dict(_last_run)


def start_scheduler() -> None:
    global _scheduler
    if not SYNC_ENABLED:
        logger.info("GARMIN_SYNC_ENABLED=false; in-app Garmin scheduler disabled.")
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_scheduled_sync,
        CronTrigger(day_of_week=SYNC_DAY_OF_WEEK, hour=SYNC_HOUR_UTC, minute=0),
        id="garmin-weekly-sync",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        "In-app Garmin scheduler started: weekly on %s %02d:00 UTC.",
        SYNC_DAY_OF_WEEK,
        SYNC_HOUR_UTC,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("In-app Garmin scheduler stopped.")
