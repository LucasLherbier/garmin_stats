"""One-time local login; print GARMINTOKENS secret for GitHub Actions."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from utils.pipeline.garmin_cookies import get_garmin_client, load_credentials


def main() -> int:
    email, password = load_credentials()
    if not email or not password:
        print("Set USER_EMAIL and USER_PASSWORD in .env", file=sys.stderr)
        return 1
    client = get_garmin_client(email, password)
    if not client:
        return 1
    garth_client = getattr(client, "garth", None)
    if garth_client is None or not hasattr(garth_client, "dumps"):
        print("garminconnect client has no garth.dumps(); check garminconnect version.", file=sys.stderr)
        return 1
    blob = garth_client.dumps()
    print("\n--- Add repo secret GARMINTOKENS (entire line below) ---\n")
    print(blob)
    print("\n--- End GARMINTOKENS ---\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
