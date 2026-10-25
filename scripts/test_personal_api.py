"""Standalone field-parity test for the Garmin Personal API client."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from utils.pipeline.garmin_personal_api import GarminPersonalAPI  # noqa: E402

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"  [{'OK' if ok else 'MANQUANT'}] {name} {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Garmin Personal API parity test.")
    parser.add_argument("--days", type=int, default=14, help="Lookback window in days.")
    args = parser.parse_args()

    end = date.today()
    start = end - timedelta(days=args.days - 1)
    start_s, end_s = start.isoformat(), end.isoformat()

    print(f"== Garmin Personal API test: {start_s} -> {end_s} ==\n")

    client = GarminPersonalAPI()

    print("1) Token")
    token = client._get_token()
    check("JWT mint", bool(token), f"({len(token)} chars)")

    print("\n2) Activity search")
    activities = client.get_activities_by_date(start_s, end_s)
    check("activities returned", len(activities) > 0, f"({len(activities)} found)")
    if activities:
        first = activities[0]
        print(f"     sample keys: {sorted(first.keys())[:12]} ...")

    activity_id = activities[0].get("activityId") if activities else None

    if activity_id:
        print(f"\n3) Activity detail ({activity_id})")
        detail = client.get_activity(activity_id)
        summary = detail.get("summaryDTO", {})
        check("summaryDTO present", bool(summary), f"({len(summary)} fields)")
        check(
            "trainingEffect",
            summary.get("trainingEffect") is not None,
            f"= {summary.get('trainingEffect')}",
        )
        check(
            "trainingEffectLabel",
            summary.get("trainingEffectLabel") is not None,
            f"= {summary.get('trainingEffectLabel')}",
        )
        check(
            "differenceBodyBattery",
            summary.get("differenceBodyBattery") is not None,
            f"= {summary.get('differenceBodyBattery')}",
        )

        print(f"\n4) FIT download ({activity_id})")
        fit_bytes = client.download_activity(activity_id)
        check("FIT bytes", len(fit_bytes) > 100, f"({len(fit_bytes)} bytes)")
        try:
            import io

            from fitparse import FitFile

            parsed = FitFile(io.BytesIO(fit_bytes))
            records = sum(1 for _ in parsed.get_messages("record"))
            laps = sum(1 for _ in parsed.get_messages("lap"))
            check("FIT parses (fitparse)", True, f"({records} records, {laps} laps)")
        except ImportError:
            print("     fitparse not installed — skipped FIT parsing.")
        except Exception as exc:  # noqa: BLE001
            check("FIT parses (fitparse)", False, str(exc))

    print("\n5) Daily summaries (resting HR / stress / Body Battery in one call)")
    try:
        dailies = client.get_daily_summaries((end - timedelta(days=6)).isoformat(), end_s)
        rows = dailies if isinstance(dailies, list) else []
        check("daily summary rows", len(rows) > 0, f"({len(rows)} days)")
        if rows:
            sample = rows[-1]
            print(f"     sample keys: {sorted(sample.keys())}")
            hr = sample.get("heartRate") or {}
            bb = sample.get("bodyBattery") or {}
            check(
                "resting HR",
                hr.get("restingValue") is not None,
                f"= {hr.get('restingValue')}",
            )
            check(
                "body battery end-of-day",
                bb.get("endOfDayValue") is not None,
                f"= {bb.get('endOfDayValue')}",
            )
    except Exception as exc:  # noqa: BLE001
        check("daily summaries call", False, str(exc))

    print("\n6) Sleep summaries (7 days)")
    try:
        sleep = client.get_sleep_summaries((end - timedelta(days=6)).isoformat(), end_s)
        rows = sleep if isinstance(sleep, list) else []
        check("sleep rows", len(rows) > 0, f"({len(rows)} nights)")
        if rows:
            sample = rows[-1]
            print(f"     sample keys: {sorted(sample.keys())}")
            scores = sample.get("sleepScores") or {}
            overall = scores.get("overall") or {}
            check(
                "sleep score",
                overall.get("value") is not None,
                f"= {overall.get('value')}",
            )
            for field in (
                "deepSleepSeconds",
                "lightSleepSeconds",
                "remSleepSeconds",
                "awakeSleepSeconds",
            ):
                check(
                    f"sleep field {field}",
                    sample.get(field) is not None,
                    f"= {sample.get(field)}",
                )
    except Exception as exc:  # noqa: BLE001
        check("sleep summaries call", False, str(exc))

    print("\n7) HRV daily (7 days)")
    try:
        hrv = client.get_hrv_daily((end - timedelta(days=6)).isoformat(), end_s)
        rows = (hrv or {}).get("hrvSummaries", []) if isinstance(hrv, dict) else []
        check("HRV rows", len(rows) > 0, f"({len(rows)} nights)")
        if rows:
            sample = rows[-1]
            check(
                "lastNightAvg",
                sample.get("lastNightAvg") is not None,
                f"= {sample.get('lastNightAvg')}",
            )
            check(
                "weeklyAvg",
                sample.get("weeklyAvg") is not None,
                f"= {sample.get('weeklyAvg')}",
            )
            check(
                "baseline band",
                isinstance(sample.get("baseline"), dict),
                f"= {sample.get('baseline')}",
            )
    except Exception as exc:  # noqa: BLE001
        check("HRV call", False, str(exc))

    print("\n== Checklist ==")
    failed = 0
    for name, ok, detail in CHECKS:
        print(f"  {'OK      ' if ok else 'MANQUANT'}  {name} {detail}")
        failed += 0 if ok else 1
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} checks OK.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
