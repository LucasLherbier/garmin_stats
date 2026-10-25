"""Garmin Personal API client (official API, personal tier).

NEW WAY — default when GARMIN_SOURCE=personal_api (or unset).
OLD WAY: unofficial `garminconnect` + GARMINTOKENS — see `garmin_cookies.py`
(set GARMIN_SOURCE=legacy to restore it).

Auth: GARMIN_PERSONAL_API_KEY -> JWT (24 h), no cookies or login.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import time
import zipfile
from datetime import date, timedelta
from enum import Enum

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://personal.connectapi.garmin.com"
TOKEN_URL = f"{BASE_URL}/personalapitoken-service/personal-api/personal-api-key/token"
FIT_ACCEPT = "application/zip, application/x-zip-compressed, application/octet-stream"

SEARCH_WINDOW_DAYS = 30
SEARCH_PAGE_LIMIT = 20


class GarminPersonalAPIError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class UnsupportedFormatError(GarminPersonalAPIError):
    """Personal API serves original FIT only (no GPX/TCX/CSV exports)."""


class GarminPersonalAPI:
    class ActivityDownloadFormat(Enum):
        ORIGINAL = "ORIGINAL"
        GPX = "GPX"
        TCX = "TCX"
        CSV = "CSV"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        min_request_interval_sec: float = 0.5,
        timeout_sec: int = 60,
    ):
        self._api_key = api_key or os.getenv("GARMIN_PERSONAL_API_KEY")
        if not self._api_key:
            raise GarminPersonalAPIError(
                "GARMIN_PERSONAL_API_KEY is not set. Create a key in "
                "Garmin Connect (Settings -> Personal API Key)."
            )
        self._min_interval = min_request_interval_sec
        self._timeout = timeout_sec
        self._session = requests.Session()
        self._token: str | None = None
        self._token_exp: float = 0.0
        self._last_request_at: float = 0.0

    def _mint_token(self) -> str:
        resp = self._session.post(
            TOKEN_URL,
            headers={
                "Authorization": f"ApiKey {self._api_key}",
                "Accept": "*/*",
            },
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise GarminPersonalAPIError(
                f"Token request failed: HTTP {resp.status_code} {resp.text[:200]}",
                status=resp.status_code,
            )
        token = resp.text.strip()
        exp = time.time() + 24 * 3600
        try:
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            exp = float(payload.get("exp", exp))
        except Exception:  # noqa: BLE001
            logger.debug("Could not decode JWT exp; assuming 24 h validity.")
        self._token = token
        self._token_exp = exp
        logger.info(
            "Garmin Personal API token minted (expires in ~%dh).",
            max(0, int((exp - time.time()) // 3600)),
        )
        return token

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_exp - 3600:
            return self._token
        return self._mint_token()

    def _pace(self) -> None:
        wait = self._min_interval - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)

    def _request(
        self,
        method: str,
        path: str,
        *,
        accept: str = "application/json",
        params: dict | None = None,
        _retry_auth: bool = True,
    ):
        self._pace()
        resp = self._session.request(
            method,
            f"{BASE_URL}{path}",
            headers={
                "Authorization": f"Bearer {self._get_token()}",
                "Accept": accept,
            },
            params=params,
            timeout=self._timeout,
        )
        self._last_request_at = time.monotonic()
        if resp.status_code == 401 and _retry_auth:
            self._token = None
            return self._request(
                method, path, accept=accept, params=params, _retry_auth=False
            )
        return resp

    def _get_json(self, path: str, params: dict | None = None):
        resp = self._request("GET", path, params=params)
        if resp.status_code == 204:
            return None
        if resp.status_code != 200:
            raise GarminPersonalAPIError(
                f"GET {path} failed: HTTP {resp.status_code} {resp.text[:200]}",
                status=resp.status_code,
            )
        return resp.json()

    def get_activities_by_date(self, startdate: str, enddate: str) -> list[dict]:
        start = date.fromisoformat(startdate)
        end = date.fromisoformat(enddate)
        results: list[dict] = []
        window_start = start
        while window_start <= end:
            window_end = min(window_start + timedelta(days=SEARCH_WINDOW_DAYS - 1), end)
            results.extend(self._search_window(window_start, window_end))
            window_start = window_end + timedelta(days=1)
        return results

    def _search_window(self, start: date, end: date) -> list[dict]:
        try:
            return self._search_window_paged(start, end)
        except GarminPersonalAPIError as exc:
            if exc.status == 500 and end > start:
                mid = start + (end - start) // 2
                logger.warning(
                    "Activity search 500 on %s..%s; splitting window.", start, end
                )
                return self._search_window(start, mid) + self._search_window(
                    mid + timedelta(days=1), end
                )
            raise

    def _search_window_paged(self, start: date, end: date) -> list[dict]:
        activities: list[dict] = []
        offset = 0
        while True:
            page = self._get_json(
                "/activitylist-service/activities/search/activities",
                params={
                    "startDate": start.isoformat(),
                    "endDate": end.isoformat(),
                    "start": offset,
                    "limit": SEARCH_PAGE_LIMIT,
                },
            )
            if not page:
                break
            activities.extend(page)
            if len(page) < SEARCH_PAGE_LIMIT:
                break
            offset += len(page)
        return activities

    def get_activity(self, activity_id: int | str) -> dict:
        return self._get_json(f"/activity-service/activity/{activity_id}") or {}

    def download_activity(self, activity_id: int | str, dl_fmt=None) -> bytes:
        fmt = dl_fmt or self.ActivityDownloadFormat.ORIGINAL
        if fmt is not self.ActivityDownloadFormat.ORIGINAL:
            raise UnsupportedFormatError(
                f"{fmt.value} export is not available via the Personal API (FIT only)."
            )
        resp = self._request(
            "GET",
            f"/download-service/files/activity/{activity_id}",
            accept=FIT_ACCEPT,
        )
        if resp.status_code != 200:
            raise GarminPersonalAPIError(
                f"FIT download failed: HTTP {resp.status_code}",
                status=resp.status_code,
            )
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = zf.namelist()
            if not names:
                raise GarminPersonalAPIError("FIT download returned an empty ZIP.")
            return zf.read(names[0])

    def get_daily_summaries(self, start: str, end: str):
        return self._get_json(
            "/usersummary-service/v2/dailysummaries",
            params={"startDate": start, "endDate": end},
        )

    def get_sleep_summaries(self, start: str, end: str):
        return self._get_json(
            "/sleep-service/sleep/dailySleepSummariesByDate",
            params={"startDate": start, "endDate": end},
        )

    def get_hrv_daily(self, start: str, end: str):
        return self._get_json(f"/hrv-service/hrv/daily/{start}/{end}")

    def get_stress_daily(self, start: str, end: str):
        return self._get_json(
            f"/usersummary-service/stats/stress/daily/{start}/{end}"
        )

    def get_body_battery_daily(self, start: str, end: str):
        return self._get_json(
            "/wellness-service/wellness/bodyBattery/reports/daily",
            params={"startDate": start, "endDate": end},
        )
