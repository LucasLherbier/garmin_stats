"""Wellness fetch via Garmin Personal API (range endpoints)."""

from __future__ import annotations

import logging
from typing import Any

from utils.pipeline.daily_wellness.extract import (
    iter_date_chunks,
    parse_body_battery_day_item,
    parse_hrv_payload,
    parse_sleep_payload,
    parse_stress_payload,
)
from utils.pipeline.garmin_personal_api import GarminPersonalAPI

logger = logging.getLogger(__name__)


def _day_key(item: dict, *keys: str) -> str:
    for key in keys:
        raw = item.get(key)
        if raw:
            return str(raw)[:10]
    return ""


def _as_list(payload: Any) -> list:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    return []


def _merge_daily_summaries(
    merged: dict[str, dict], payload: list[dict]
) -> None:
    for item in payload:
        if not isinstance(item, dict):
            continue
        day = _day_key(item, "calendarDate", "date")
        if not day:
            continue
        entry = merged.setdefault(day, {})
        hr = item.get("heartRate") if isinstance(item.get("heartRate"), dict) else {}
        if hr.get("restingValue") is not None:
            entry["resting_hr"] = int(hr["restingValue"])
        if item.get("totalSteps") is not None:
            entry["daily_steps"] = int(item["totalSteps"])
        calories = item.get("totalKilocalories") or item.get("activeKilocalories")
        if calories is not None:
            entry["daily_calories"] = int(calories)
        stress = item.get("averageStressLevel") or item.get("avgStressLevel")
        if stress is not None:
            entry["avg_stress"] = int(stress)


def fetch_wellness_by_day(
    client: GarminPersonalAPI, since: str, until: str
) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    try:
        dailies = _as_list(client.get_daily_summaries(since, until))
        _merge_daily_summaries(merged, dailies)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Personal API daily summaries failed: %s", exc)

    for chunk_start, chunk_end in iter_date_chunks(since, until, 31):
        try:
            sleep_rows = _as_list(client.get_sleep_summaries(chunk_start, chunk_end))
            for item in sleep_rows:
                if not isinstance(item, dict):
                    continue
                day = _day_key(item, "calendarDate", "sleepStartTimestampGMT")
                if not day and item.get("dailySleepDTO"):
                    day = _day_key(item["dailySleepDTO"], "calendarDate")
                if not day:
                    continue
                merged.setdefault(day, {}).update(
                    parse_sleep_payload(item if "dailySleepDTO" not in item else item)
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Personal API sleep chunk %s..%s: %s", chunk_start, chunk_end, exc)

        try:
            bb_rows = _as_list(client.get_body_battery_daily(chunk_start, chunk_end))
            for item in bb_rows:
                if not isinstance(item, dict):
                    continue
                day = _day_key(item, "date", "calendarDate")
                if day:
                    merged.setdefault(day, {}).update(parse_body_battery_day_item(item))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Personal API body battery chunk %s..%s: %s", chunk_start, chunk_end, exc
            )

    for chunk_start, chunk_end in iter_date_chunks(since, until, 28):
        try:
            stress = client.get_stress_daily(chunk_start, chunk_end)
            for item in _as_list(stress):
                if not isinstance(item, dict):
                    continue
                day = _day_key(item, "calendarDate", "date")
                if day:
                    merged.setdefault(day, {}).update(parse_stress_payload(item))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Personal API stress chunk %s..%s: %s", chunk_start, chunk_end, exc)

    for chunk_start, chunk_end in iter_date_chunks(since, until, 7):
        try:
            hrv_payload = client.get_hrv_daily(chunk_start, chunk_end)
            summaries = []
            if isinstance(hrv_payload, dict):
                summaries = hrv_payload.get("hrvSummaries") or []
            for item in _as_list(summaries):
                if not isinstance(item, dict):
                    continue
                day = _day_key(item, "calendarDate", "date")
                if day:
                    merged.setdefault(day, {}).update(parse_hrv_payload(item))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Personal API HRV chunk %s..%s: %s", chunk_start, chunk_end, exc)

    for day, row in merged.items():
        has_data = any(
            row.get(k) is not None
            for k in (
                "sleep_score",
                "sleep_duration_sec",
                "hrv_last_night_avg",
                "resting_hr",
                "daily_steps",
                "body_battery_high",
            )
        )
        row["day"] = day
        row["extract_status"] = "ok" if has_data else "no_data"

    return merged
