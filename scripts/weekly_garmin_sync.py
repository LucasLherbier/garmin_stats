"""Single Garmin sync for CI / manual runs: activities, summaries, daily wellness."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from utils.pipeline.run_garmin_sync import run_garmin_sync, sync_start_date

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly Garmin sync.")
    parser.add_argument(
        "--start_date",
        help="Activity extract start (YYYY-MM-DD). Default: 14 days ago.",
    )
    args = parser.parse_args()
    start = args.start_date or sync_start_date()
    logger.info("Garmin sync from %s", start)
    run_garmin_sync(start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
