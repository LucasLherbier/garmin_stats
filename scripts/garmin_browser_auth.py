#!/usr/bin/env python3
"""
Get Garmin OAuth tokens via a real browser (Playwright).
Use when programmatic login is 429-blocked and export_garmin_tokens.py fails.

Setup:
  pip install playwright requests requests-oauthlib
  python -m playwright install chromium

Run (from repo root, USER_EMAIL / USER_PASSWORD in .env):
  python scripts/garmin_browser_auth.py

Prints a GARMINTOKENS blob for GitHub Actions (same format as export_garmin_tokens.py).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

OAUTH_CONSUMER_URL = "https://thegarth.s3.amazonaws.com/oauth_consumer.json"
ANDROID_UA = "com.garmin.android.apps.connectmobile"
SSO_URL = (
    "https://sso.garmin.com/sso/embed"
    "?id=gauth-widget"
    "&embedWidget=true"
    "&gauthHost=https://sso.garmin.com/sso"
    "&clientId=GarminConnect"
    "&locale=en_US"
    "&redirectAfterAccountLoginUrl=https://sso.garmin.com/sso/embed"
    "&service=https://sso.garmin.com/sso/embed"
)


def get_oauth_consumer() -> dict:
    resp = requests.get(OAUTH_CONSUMER_URL, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_oauth1_token(ticket: str, consumer: dict) -> dict:
    sess = OAuth1Session(consumer["consumer_key"], consumer["consumer_secret"])
    url = (
        "https://connectapi.garmin.com/oauth-service/oauth/preauthorized"
        f"?ticket={ticket}"
        "&login-url=https://sso.garmin.com/sso/embed"
        "&accepts-mfa-tokens=true"
    )
    resp = sess.get(url, headers={"User-Agent": ANDROID_UA}, timeout=15)
    resp.raise_for_status()
    parsed = __import__("urllib.parse").parse_qs(resp.text)
    token = {k: v[0] for k, v in parsed.items()}
    token["domain"] = "garmin.com"
    return token


def exchange_oauth2(oauth1: dict, consumer: dict) -> dict:
    sess = OAuth1Session(
        consumer["consumer_key"],
        consumer["consumer_secret"],
        resource_owner_key=oauth1["oauth_token"],
        resource_owner_secret=oauth1["oauth_token_secret"],
    )
    url = "https://connectapi.garmin.com/oauth-service/oauth/exchange/user/2.0"
    data = {}
    if oauth1.get("mfa_token"):
        data["mfa_token"] = oauth1["mfa_token"]
    resp = sess.post(
        url,
        headers={
            "User-Agent": ANDROID_UA,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=data,
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json()
    token["expires_at"] = int(time.time() + token["expires_in"])
    token["refresh_token_expires_at"] = int(time.time() + token["refresh_token_expires_in"])
    return token


def browser_login(email: str, password: str) -> str:
    from playwright.sync_api import sync_playwright

    ticket = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(SSO_URL)

        try:
            page.get_by_label("Email").fill(email, timeout=5000)
            page.get_by_label("Password").fill(password, timeout=5000)
        except Exception:
            pass

        print()
        print("=" * 50)
        print("  Complete login in the browser (MFA if prompted).")
        print("  This window closes when a ticket is captured.")
        print("=" * 50)
        print()

        deadline = time.time() + 300
        while time.time() < deadline:
            try:
                for source in (page.content(), page.url):
                    match = re.search(r"ticket=(ST-[A-Za-z0-9\-]+)", source)
                    if match:
                        ticket = match.group(1)
                        break
                if ticket:
                    break
            except Exception:
                pass
            page.wait_for_timeout(500)

        browser.close()

    if not ticket:
        print("ERROR: No SSO ticket within 5 minutes.", file=sys.stderr)
        raise SystemExit(1)
    return ticket


def _garth_blob(oauth1: dict, oauth2: dict) -> str:
    import garth
    from garth.auth_tokens import OAuth1Token, OAuth2Token

    o1 = OAuth1Token(
        oauth_token=oauth1["oauth_token"],
        oauth_token_secret=oauth1["oauth_token_secret"],
        mfa_token=oauth1.get("mfa_token"),
        domain=oauth1.get("domain") or "garmin.com",
    )
    o2 = OAuth2Token(**oauth2)
    garth.client.configure(oauth1_token=o1, oauth2_token=o2, domain=o1.domain or "garmin.com")
    return garth.dumps()


def _save_token_dir(oauth1: dict, oauth2: dict, token_dir: Path) -> None:
    token_dir.mkdir(parents=True, exist_ok=True)
    (token_dir / "oauth1_token.json").write_text(json.dumps(oauth1, indent=2), encoding="utf-8")
    (token_dir / "oauth2_token.json").write_text(json.dumps(oauth2, indent=2), encoding="utf-8")


def main() -> int:
    email = os.getenv("USER_EMAIL", "").strip()
    password = os.getenv("USER_PASSWORD", "").strip()
    if not email or not password:
        print("Set USER_EMAIL and USER_PASSWORD in .env", file=sys.stderr)
        return 1

    print("Garmin browser auth")
    consumer = get_oauth_consumer()
    ticket = browser_login(email, password)
    oauth1 = get_oauth1_token(ticket, consumer)
    oauth2 = exchange_oauth2(oauth1, consumer)

    verify = requests.get(
        "https://connectapi.garmin.com/userprofile-service/socialProfile",
        headers={
            "User-Agent": "GCM-iOS-5.7.2.1",
            "Authorization": f"Bearer {oauth2['access_token']}",
        },
        timeout=15,
    )
    verify.raise_for_status()
    profile = verify.json()
    print(f"Authenticated as: {profile.get('displayName', 'unknown')}")

    token_dir = _ROOT / ".garmin_tokens"
    _save_token_dir(oauth1, oauth2, token_dir)
    print(f"Token files saved to {token_dir}")

    blob = _garth_blob(oauth1, oauth2)
    print("\n--- GitHub → Settings → Secrets → Actions → GARMINTOKENS (whole line) ---\n")
    print(blob)
    print("\n--- End GARMINTOKENS ---\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
