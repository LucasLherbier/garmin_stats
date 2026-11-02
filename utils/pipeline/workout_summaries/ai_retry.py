"""Retry pass for failed AI summaries — coded, not just described.

Why: process_workout_summaries_incremental skips existing rows, so an
activity that fell back during a quota outage would keep its
heuristic label forever. This pass finds workout_summaries rows whose
ai_status is retryable (ai_summary.RETRYABLE_STATUSES), regenerates
them through the normal pipeline, and replaces ONLY the rows whose
new ai_status is 'ok' — a still-failing activity keeps its existing
row (no delete), but its ai_attempts counter is incremented by
UPDATE, so the candidate query's MAX_AI_ATTEMPTS cap is actually
reached and hopeless rows stop consuming quota.

Honesty note on atomicity: save_workout_summaries(replace_existing=
True) deletes then uploads, and upload_to_bigquery swallows its
errors into a False return. If that ever returns False here, the
affected ids are logged at ERROR level — they are the rows to
reprocess manually. Watch for the log line after each run.

Run after the daily sync, bounded:
    python -m utils.pipeline.workout_summaries.ai_retry --limit 50
    python -m utils.pipeline.workout_summaries.ai_retry --limit 50 --dry-run

Designed to live in utils/pipeline/workout_summaries/.
"""

from __future__ import annotations

import argparse
import logging

# process / utils_gcp are imported lazily inside the functions so
# this module (and its SQL builder) stays importable anywhere.
try:  # installed in the repo package
    from utils.pipeline.workout_summaries.ai_summary import (
        MAX_AI_ATTEMPTS,
        RETRYABLE_STATUSES,
        ai_needs_retry,
    )
except ImportError:  # standalone kit layout
    from ai_summary import (  # type: ignore[no-redef]
        MAX_AI_ATTEMPTS,
        RETRYABLE_STATUSES,
        ai_needs_retry,
    )

logger = logging.getLogger(__name__)

TABLE_NAME = "workout_summaries"


def _candidates_query(table_id: str, limit: int) -> str:
    """Retryable rows, filtered IN SQL.

    Filtering in Python after a LIMIT is a trap: rows that can never
    be retried (no_laps, or attempts exhausted) accumulate at the head
    of the oldest-first ordering and eventually mask every real
    candidate. The attempts cap also lives here, so a session the
    model cannot read stops consuming quota after MAX_AI_ATTEMPTS.
    """
    statuses = ", ".join(f"'{s}'" for s in sorted(RETRYABLE_STATUSES))
    return f"""
        SELECT activityId, ai_status, ai_prompt_version, ai_attempts
        FROM `{table_id}`
        WHERE ai_status IN ({statuses})
          AND COALESCE(ai_attempts, 0) < {int(MAX_AI_ATTEMPTS)}
        ORDER BY startTimeLocal ASC
        LIMIT {int(limit)}
    """


def _increment_attempts(ids: list[int]) -> None:
    """ai_attempts += 1 on the STORED rows that failed again.

    The regenerated rows for still-failing activities are never
    saved (only 'ok' rows are replaced), so the counter can only
    move here — this UPDATE is what makes MAX_AI_ATTEMPTS real.
    """
    if not ids:
        return
    from google.cloud import bigquery

    from utils.utils_gcp import _table_id, bq_client

    if bq_client is None:
        return
    table_id = _table_id(TABLE_NAME)
    query = f"""
        UPDATE `{table_id}`
        SET ai_attempts = COALESCE(ai_attempts, 0) + 1
        WHERE activityId IN UNNEST(@ids)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("ids", "INT64", [int(i) for i in ids])
        ]
    )
    bq_client.query(query, job_config=job_config).result()


def find_retry_candidates(limit: int = 50) -> list[int]:
    """activityIds whose ai_status is retryable, oldest first."""
    from utils.utils_gcp import _table_id, bq_client

    if bq_client is None:
        logger.warning("No BigQuery client — cannot look for AI retries.")
        return []
    table_id = _table_id(TABLE_NAME)
    rows = list(bq_client.query(_candidates_query(table_id, limit)).result())
    return [
        int(row["activityId"])
        for row in rows
        if ai_needs_retry(row["ai_status"], row["ai_prompt_version"])
    ]


def retry_ai_summaries(limit: int = 50, dry_run: bool = False) -> dict:
    ids = find_retry_candidates(limit)
    result: dict = {"candidates": ids, "regenerated": [], "still_failing": []}
    if not ids:
        logger.info("AI retry: no candidates.")
        return result
    if dry_run:
        logger.info("AI retry (dry run): %s candidate(s): %s", len(ids), ids)
        return result
    from utils.pipeline.workout_summaries.process import (
        build_workout_summaries,
        save_workout_summaries,
    )

    df = build_workout_summaries(activity_ids=ids, skip_existing=False)
    if df.empty:
        logger.warning("AI retry: pipeline returned no rows for %s", ids)
        result["still_failing"] = ids
        _increment_attempts(ids)
        return result
    ok_df = df[df["ai_status"] == "ok"]
    result["regenerated"] = ok_df["activityId"].astype(int).tolist()
    result["still_failing"] = (
        df[df["ai_status"] != "ok"]["activityId"].astype(int).tolist()
    )
    _increment_attempts(result["still_failing"])
    if not ok_df.empty:
        saved = save_workout_summaries(ok_df, replace_existing=True)
        result["saved"] = bool(saved)
        if not saved:
            logger.error(
                "AI retry: upload FAILED after delete for activityIds %s — "
                "these workout_summaries rows must be reprocessed manually.",
                result["regenerated"],
            )
    logger.info(
        "AI retry: %s regenerated, %s still failing.",
        len(result["regenerated"]),
        len(result["still_failing"]),
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retry failed AI summaries")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(retry_ai_summaries(limit=args.limit, dry_run=args.dry_run))
