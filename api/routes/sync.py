from fastapi import APIRouter

from api.sync_scheduler import get_sync_status, trigger_manual_sync

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/trigger")
def trigger_sync():
    """Start a Garmin sync in the background. Returns immediately (202-style)."""
    return trigger_manual_sync()


@router.get("/status")
def sync_status():
    """Last sync run outcome (never_run / running / success / failed)."""
    return get_sync_status()
