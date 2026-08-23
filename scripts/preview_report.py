"""Generate and open an activity HTML report preview in the default browser."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

import pandas as pd

from actions.activity_splits import parse_laps_field, resolve_sport
from actions.parse_tcx_csv import parse_tcx_to_dataframe
from actions.power_curve import power_profile_from_fit, power_profile_from_telemetry
from actions.report_html import build_activity_report_html, build_list_aggregates
from actions.report_map import gpx_track_points
from tabs.tab_report import _load_report_assets
from utils import sql_queries as sql
from utils.utils_gcp import query_bigquery_live


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview HTML activity report in browser.")
    parser.add_argument("activity_id", type=int)
    parser.add_argument(
        "--lists",
        nargs="*",
        default=None,
        help='Split lists as "7,8,9" "14,15,16" (1-based split numbers)',
    )
    parser.add_argument(
        "--list-names",
        nargs="*",
        default=None,
        help="Optional names for each list",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: Downloads/report_<id>_preview.html)",
    )
    args = parser.parse_args()

    detail_df = query_bigquery_live(sql.get_activity_report_query(args.activity_id))
    if detail_df.empty:
        print(f"Activity {args.activity_id} not found.")
        return 1

    detail = detail_df.iloc[0]
    sport = resolve_sport(detail)
    laps = parse_laps_field(detail.get("laps"))

    list_aggregates = None
    if args.lists and laps:
        split_to_idx = {lap.get("split", i + 1): i for i, lap in enumerate(laps)}
        list_picks = []
        for spec in args.lists:
            indices = []
            for part in spec.split(","):
                part = part.strip()
                if not part:
                    continue
                key = int(part)
                if key in split_to_idx:
                    indices.append(split_to_idx[key])
                elif 0 <= key - 1 < len(laps):
                    indices.append(key - 1)
            if indices:
                list_picks.append(indices)
        if list_picks:
            list_aggregates = build_list_aggregates(
                laps, list_picks, sport, list_names=args.list_names
            )

    power_profile, hr_series, track_points = _load_report_assets(
        args.activity_id, detail.get("startTimeLocal"), sport
    )

    html_doc = build_activity_report_html(
        detail,
        laps,
        list_aggregates=list_aggregates,
        power_profile=power_profile,
        hr_series=hr_series,
        track_points=track_points,
    )

    out = args.out or Path.home() / "Downloads" / f"report_{args.activity_id}_preview.html"
    out.write_text(html_doc, encoding="utf-8")
    print(f"Wrote {out}")
    webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
