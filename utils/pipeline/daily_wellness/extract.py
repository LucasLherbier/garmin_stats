"""Fetch daily wellness metrics from Garmin Connect."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Iterator

logger = logging.getLogger(__name__)

BODY_BATTERY_CHUNK_DAYS = 365
RHR_CHUNK_DAYS = 90


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick(mapping: dict | None, *keys: str) -> Any:
    if not mapping:
        return None
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def iter_date_chunks(since: str, until: str, chunk_days: int) -> Iterator[tuple[str, str]]:
    start = datetime.strptime(since, "%Y-%m-%d").date()
    end = datetime.strptime(until, "%Y-%m-%d").date()
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        yield current.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
        current = chunk_end + timedelta(days=1)


def _call_with_retry(label: str, fn: Callable[[], Any], *, day: str = "", max_retries: int = 5) -> Any:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            message = str(exc)
            if "429" in message and attempt < max_retries - 1:
                wait = min(120, 5 * (2**attempt))
                logger.warning(
                    "Garmin rate limit on %s for %s — retry %s/%s in %ss",
                    label,
                    day or "range",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                time.sleep(wait)
                continue
            logger.debug("Garmin %s failed for %s: %s", label, day or "range", exc)
            return None
    logger.debug("Garmin %s failed for %s after retries: %s", label, day or "range", last_exc)
    return None


def parse_sleep_payload(payload: dict | None) -> dict[str, int | None]:
    body = _pick(payload, "dailySleepDTO") or payload or {}
    sleep_scores = body.get("sleepScores") if isinstance(body.get("sleepScores"), dict) else {}
    overall = sleep_scores.get("overall") if isinstance(sleep_scores.get("overall"), dict) else {}
    sleep_score = overall.get("value") if overall else body.get("sleepScore")
    return {
        "sleep_score": _as_int(sleep_score),
        "sleep_duration_sec": _as_int(body.get("sleepTimeSeconds")),
        "sleep_deep_sec": _as_int(body.get("deepSleepSeconds")),
        "sleep_light_sec": _as_int(body.get("lightSleepSeconds")),
        "sleep_rem_sec": _as_int(body.get("remSleepSeconds")),
        "sleep_awake_sec": _as_int(body.get("awakeSleepSeconds")),
    }


def parse_hrv_payload(payload: dict | None) -> dict[str, int | float | str | None]:
    summary = _pick(payload, "hrvSummary") or payload or {}
    return {
        "hrv_last_night_avg": _as_float(summary.get("lastNightAvg")),
        "hrv_status": summary.get("status"),
        "hrv_weekly_avg": _as_float(summary.get("weeklyAvg")),
    }


def parse_stats_payload(payload: dict | None) -> dict[str, int | None]:
    body = payload or {}
    resting_hr = body.get("restingHeartRate")
    dto = body.get("restingHeartRateDTO")
    if isinstance(dto, dict) and dto.get("restingHeartRate") is not None:
        resting_hr = dto.get("restingHeartRate")
    return {
        "resting_hr": _as_int(resting_hr),
        "daily_steps": _as_int(body.get("totalSteps") or body.get("steps")),
        "daily_calories": _as_int(
            body.get("totalKilocalories") or body.get("activeKilocalories") or body.get("calories")
        ),
    }


def parse_body_battery_day_item(item: dict) -> dict[str, int | None]:
    arr = item.get("bodyBatteryValuesArray") or []
    vals = [
        _as_int(point[1])
        for point in arr
        if isinstance(point, list) and len(point) > 1 and point[1] is not None
    ]
    vals = [value for value in vals if value is not None]
    if vals:
        return {"body_battery_high": max(vals), "body_battery_low": min(vals)}
    return {
        "body_battery_high": _as_int(item.get("charged")),
        "body_battery_low": None,
    }


def parse_stress_payload(payload: dict | None) -> dict[str, int | None]:
    body = payload or {}
    return {
        "avg_stress": _as_int(
            _pick(body, "avgStressLevel")
            or _pick(body, "averageStressLevel")
            or _pick(body, "overallStressLevel")
        ),
    }


def fetch_bulk_body_battery(client, since: str, until: str) -> dict[str, dict[str, int | None]]:
    merged: dict[str, dict[str, int | None]] = {}
    for chunk_start, chunk_end in iter_date_chunks(since, until, BODY_BATTERY_CHUNK_DAYS):
        payload = _call_with_retry(
            "body_battery",
            lambda s=chunk_start, e=chunk_end: client.get_body_battery(s, e),
        )
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            day = str(item.get("date", ""))[:10]
            if day:
                merged[day] = parse_body_battery_day_item(item)
    return merged


def fetch_bulk_resting_hr(client, since: str, until: str) -> dict[str, int]:
    merged: dict[str, int] = {}
    display_name = client._require_display_name()
    url = f"{client.garmin_connect_rhr_url}/{display_name}"

    for chunk_start, chunk_end in iter_date_chunks(since, until, RHR_CHUNK_DAYS):
        payload = _call_with_retry(
            "resting_hr",
            lambda s=chunk_start, e=chunk_end: client.connectapi(
                url,
                params={"fromDate": s, "untilDate": e, "metricId": 60},
            ),
        )
        if not isinstance(payload, dict):
            continue
        metrics = (payload.get("allMetrics") or {}).get("metricsMap") or {}
        items = metrics.get("WELLNESS_RESTING_HEART_RATE") or []
        for item in items:
            if not isinstance(item, dict):
                continue
            day = str(item.get("calendarDate", ""))[:10]
            value = _as_int(item.get("value"))
            if day and value is not None:
                merged[day] = value
    return merged


def fetch_day_wellness(
    client,
    day: str,
    *,
    prefetched: dict[str, dict[str, Any]] | None = None,
    request_delay_sec: float = 0.0,
    include_stress: bool = False,
) -> dict[str, Any]:
    """Pull per-day Garmin endpoints (sleep, HRV, stats). Bulk metrics come via prefetched."""
    row: dict[str, Any] = {"day": day}
    errors: list[str] = []
    prefetched = prefetched or {}

    if day in prefetched:
        row.update(prefetched[day])

    def _call(label: str, fn: Callable[[], Any]):
        result = _call_with_retry(label, fn, day=day)
        if result is None:
            errors.append(label)
        return result

    sleep_payload = _call("sleep", lambda: client.get_sleep_data(day))
    if request_delay_sec:
        time.sleep(request_delay_sec)
    hrv_payload = _call("hrv", lambda: client.get_hrv_data(day))
    if request_delay_sec:
        time.sleep(request_delay_sec)
    stats_payload = _call("stats", lambda: client.get_stats(day))

    row.update(parse_sleep_payload(sleep_payload if isinstance(sleep_payload, dict) else None))
    row.update(parse_hrv_payload(hrv_payload if isinstance(hrv_payload, dict) else None))
    stats = parse_stats_payload(stats_payload if isinstance(stats_payload, dict) else None)
    if row.get("resting_hr") is None and stats.get("resting_hr") is not None:
        row["resting_hr"] = stats["resting_hr"]
    elif stats.get("resting_hr") is not None:
        row["resting_hr"] = stats["resting_hr"]
    row["daily_steps"] = stats.get("daily_steps")
    row["daily_calories"] = stats.get("daily_calories")

    if include_stress:
        stress_payload = _call("stress", lambda: client.get_stress_data(day))
        row.update(parse_stress_payload(stress_payload if isinstance(stress_payload, dict) else None))

    has_sleep = row.get("sleep_score") is not None or row.get("sleep_duration_sec") is not None
    has_hrv = row.get("hrv_last_night_avg") is not None
    has_stats = any(row.get(k) is not None for k in ("resting_hr", "daily_steps", "daily_calories"))
    has_battery = row.get("body_battery_high") is not None

    if has_sleep or has_hrv or has_stats or has_battery:
        row["extract_status"] = "partial" if errors else "ok"
    elif errors:
        row["extract_status"] = "error"
    else:
        row["extract_status"] = "no_data"

    if errors:
        row["extract_errors"] = ",".join(errors)

    return row
