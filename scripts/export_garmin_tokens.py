"""One-time local login; print GARMINTOKENS secret for GitHub Actions."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

# Set before garmin_cookies reads GARMIN_LOGIN_RETRIES (overridden by --wait-on-rate-limit).
os.environ.setdefault("GARMIN_LOGIN_RETRIES", "1")

from garminconnect import Garmin

from utils.pipeline.garmin_cookies import (
    _DEFAULT_TOKEN_DIR,
    _tokens_on_disk,
    export_token_blob,
    get_garmin_client,
    load_credentials,
)


def _print_blob(blob: str) -> None:
    print("\n--- Add repo secret GARMINTOKENS (entire line below) ---\n")
    print(blob)
    print("\n--- End GARMINTOKENS ---\n")


def _client_from_saved_tokens(token_dir: Path) -> Garmin | None:
    if not _tokens_on_disk(token_dir):
        return None
    email, password = load_credentials()
    client = Garmin(email or "tokens@local", password or "")
    try:
        client.login(tokenstore=str(token_dir))
    except Exception as exc:
        print(f"Could not load saved tokens from {token_dir}: {exc}", file=sys.stderr)
        return None
    return client


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export OAuth blob for GitHub secret GARMINTOKENS.",
    )
    parser.add_argument(
        "--from-saved",
        action="store_true",
        help="Use .garmin_tokens on disk (no password login). Try this after a past successful local login.",
    )
    parser.add_argument(
        "--wait-on-rate-limit",
        action="store_true",
        help="Retry for up to ~15 min on 429 (default: fail fast after first rate limit).",
    )
    args = parser.parse_args()

    if args.wait_on_rate_limit:
        os.environ["GARMIN_LOGIN_RETRIES"] = "5"

    if args.from_saved:
        client = _client_from_saved_tokens(_DEFAULT_TOKEN_DIR)
        if not client:
            print(
                f"No usable tokens in {_DEFAULT_TOKEN_DIR}. "
                "You need one successful password login first (when Garmin is not rate-limiting).",
                file=sys.stderr,
            )
            return 1
    else:
        email, password = load_credentials()
        if not email or not password:
            print("Set USER_EMAIL and USER_PASSWORD in .env", file=sys.stderr)
            return 1
        client = get_garmin_client(email, password)
        if not client:
            print(
                "\nGarmin login failed. If you see 429 / rate limit:\n"
                "  • Stop retrying for several hours (retries extend the block).\n"
                "  • Try another network (phone hotspot, VPN off/on).\n"
                "  • Confirm you can sign in at connect.garmin.com in a browser.\n"
                "  • Then run again with --wait-on-rate-limit if needed.\n"
                "CI will not work until this script prints a GARMINTOKENS blob.\n",
                file=sys.stderr,
            )
            return 1
    blob = export_token_blob(client)
    if not blob:
        print(
            "Could not export tokens; install garminconnect==0.3.3 (see requirements.txt) "
            "and log in locally first.",
            file=sys.stderr,
        )
        return 1
    _print_blob(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
