"""Compare heuristic vs LLM structure_summary for one activity."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv()

from utils.gemini_client import models_for_api
from utils.pipeline.workout_summaries.lap_analysis import format_lap_table
from utils.pipeline.workout_summaries.process import process_activity_row
from utils.pipeline.workout_summaries.segments import format_segments_for_log
from utils.pipeline.workout_summaries.structure_summary import build_main_structure_summary
from utils.pipeline.workout_summaries.structure_summary_llm import (
    build_structure_prompt,
    build_structure_summary_llm,
    merge_blocks_for_activity,
)
from utils.utils_gcp import GCP_DATASET_ID, bq_client

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def fetch_activity_by_id(activity_id: int):
    if bq_client is None:
        raise RuntimeError("BigQuery client is not initialized.")
    query = f"""
        SELECT
            activityId,
            startTimeLocal,
            FORMAT_DATE('%Y-%m', DATE(startTimeLocal)) AS month_key,
            Week,
            activityTypeGrouped AS sport,
            activityName,
            duration,
            distance,
            averageHR,
            averageSpeed,
            averageTemperature,
            elevationGain,
            trainingEffectLabel,
            trainingRace
        FROM `{GCP_DATASET_ID}.activities`
        WHERE activityId = {int(activity_id)}
        LIMIT 1
    """
    df = bq_client.query(query).to_dataframe()
    if df.empty:
        return None
    return df.iloc[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Test LLM structure_summary on one activity.")
    parser.add_argument("activity_id", type=int, help="Garmin activity ID")
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the Gemini user prompt (for AI Studio).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Also show lap table, heuristic segments, and BQ stored value.",
    )
    args = parser.parse_args()

    row = fetch_activity_by_id(args.activity_id)
    if row is None:
        logger.error("Activity %s not found in BigQuery activities table.", args.activity_id)
        return 1

    parsed = process_activity_row(row)
    if parsed.get("parse_status") != "ok":
        logger.error("Parse failed: %s", parsed.get("parse_status"))
        return 1

    lap_analysis = json.loads(parsed["lap_analysis"])
    segments = json.loads(parsed["segments"])
    laps = json.loads(parsed["laps"])
    phases = [r["phase"] for r in lap_analysis]

    if args.show_prompt:
        if args.verbose:
            logger.info("Gemini models: %s", ", ".join(models_for_api()))
        print(build_structure_prompt(row, laps, sport=parsed["sport"]))
        if not args.verbose:
            return 0

    llm_summary, source = build_structure_summary_llm(
        parsed["sport"],
        row,
        lap_analysis,
        segments,
        laps=laps,
        phases=phases,
    )

    print(llm_summary or "(none)")

    if args.verbose:
        merged = merge_blocks_for_activity(row, laps, sport=parsed["sport"])
        logger.info("Merged blocks:\n%s", json.dumps(merged, indent=2, ensure_ascii=False))
        heuristic = build_main_structure_summary(
            segments, parsed["sport"], row, laps, phases
        )
        logger.info(
            "Activity %s | %s | %s",
            row["activityId"],
            row.get("activityName"),
            row["startTimeLocal"],
        )
        logger.info("Source: %s", source)
        logger.info("Heuristic: %s", heuristic or "(none)")
        logger.info("Stored in BQ: %s", parsed.get("structure_summary"))
        logger.info("\n%s", format_lap_table(lap_analysis))
        if segments:
            logger.info("\nSegments (heuristic):\n%s", format_segments_for_log(segments))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
