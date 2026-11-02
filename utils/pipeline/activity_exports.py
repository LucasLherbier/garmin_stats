"""Garmin activity file exports (GPX, TCX, CSV, FIT) on GCS."""

from __future__ import annotations

import logging
from typing import Iterable

from actions.parse_fit import fit_bytes_to_gpx, fit_track_points
from utils.pipeline.fit_laps_export import fit_bytes_to_connect_lap_csv
from utils.pipeline.garmin_client import is_personal_client
from utils.utils_gcp import bucket, check_gcs_path_exists, upload_to_gcs

logger = logging.getLogger(__name__)

# (Garmin ActivityDownloadFormat enum member name, file extension, MIME type)
EXPORT_SPECS: tuple[tuple[str, str, str], ...] = (
    ("GPX", ".gpx", "application/gpx+xml"),
    ("TCX", ".tcx", "application/vnd.garmin.tcx+xml"),
    ("CSV", ".csv", "text/csv"),
    ("ORIGINAL", ".fit", "application/vnd.garmin.fit"),
)

# Personal API: FIT download only; GPX + lap CSV are derived locally.
PERSONAL_EXPORT_EXTENSIONS: tuple[str, ...] = (".fit", ".csv", ".gpx")


def activity_base_path(activity_month: str, activity_id: int) -> str:
    return f"data/raw/{activity_month}/{activity_id}"


def export_blob_path(base_path: str, activity_id: int, ext: str) -> str:
    return f"{base_path}/{activity_id}{ext}"


def information_csv_path(base_path: str, activity_id: int) -> str:
    return f"{base_path}/{activity_id}_information.csv"


def _read_fit_from_gcs(base_path: str, activity_id: int) -> bytes | None:
    if not bucket:
        return None
    fit_path = export_blob_path(base_path, activity_id, ".fit")
    if not check_gcs_path_exists(fit_path):
        return None
    return bucket.blob(fit_path).download_as_bytes()


def missing_export_extensions(base_path: str, activity_id: int) -> list[str]:
    """Extensions (e.g. '.csv') not yet present in GCS for this activity."""
    missing: list[str] = []
    for _fmt, ext, _ctype in EXPORT_SPECS:
        if not check_gcs_path_exists(export_blob_path(base_path, activity_id, ext)):
            missing.append(ext)
    return missing


def missing_personal_export_extensions(base_path: str, activity_id: int) -> list[str]:
    """Missing FIT / derived GPX / lap CSV (never Connect GPX/TCX)."""
    missing: list[str] = []
    fit_path = export_blob_path(base_path, activity_id, ".fit")
    fit_bytes: bytes | None = None

    if not check_gcs_path_exists(fit_path):
        missing.append(".fit")
    else:
        fit_bytes = _read_fit_from_gcs(base_path, activity_id)

    if not check_gcs_path_exists(export_blob_path(base_path, activity_id, ".csv")):
        missing.append(".csv")

    gpx_path = export_blob_path(base_path, activity_id, ".gpx")
    if not check_gcs_path_exists(gpx_path):
        if fit_bytes is not None and not fit_track_points(fit_bytes):
            pass
        else:
            missing.append(".gpx")

    return missing


def upload_fit_derivatives(
    fit_bytes: bytes,
    activity_id: int,
    base_path: str,
    *,
    activity_type: str | None = None,
) -> list[str]:
    """Upload FIT (if absent) plus GPX and lap CSV derived from the same bytes."""
    uploaded: list[str] = []

    fit_path = export_blob_path(base_path, activity_id, ".fit")
    if not check_gcs_path_exists(fit_path):
        upload_to_gcs(fit_bytes, fit_path, activity_id, "application/vnd.garmin.fit")
        uploaded.append(".fit")

    csv_path = export_blob_path(base_path, activity_id, ".csv")
    if not check_gcs_path_exists(csv_path):
        lap_csv = fit_bytes_to_connect_lap_csv(fit_bytes, activity_type=activity_type)
        if lap_csv is not None and not lap_csv.empty:
            upload_to_gcs(lap_csv, csv_path, activity_id, "text/csv")
            uploaded.append(".csv")

    gpx_path = export_blob_path(base_path, activity_id, ".gpx")
    if not check_gcs_path_exists(gpx_path):
        gpx_bytes = fit_bytes_to_gpx(fit_bytes)
        if gpx_bytes:
            upload_to_gcs(gpx_bytes, gpx_path, activity_id, "application/gpx+xml")
            uploaded.append(".gpx")
        else:
            logger.debug(
                "Activity %s: no GPS in FIT — skipping derived GPX.", activity_id
            )

    return uploaded


def backfill_personal_activity_exports(
    activity_id: int,
    client,
    base_path: str,
    *,
    only_extensions: Iterable[str] | None = None,
    activity_type: str | None = None,
) -> list[str]:
    """Download FIT via Personal API and derive GPX + lap CSV on GCS."""
    only = (
        {e if e.startswith(".") else f".{e}" for e in only_extensions}
        if only_extensions
        else set(PERSONAL_EXPORT_EXTENSIONS)
    )
    # Ignore legacy-only formats if an old missing list included them.
    only &= set(PERSONAL_EXPORT_EXTENSIONS)

    uploaded: list[str] = []
    fit_bytes = _read_fit_from_gcs(base_path, activity_id)

    if fit_bytes is None and (".fit" in only or only & {".csv", ".gpx"}):
        fit_bytes = client.download_activity(activity_id)
        uploaded.extend(
            upload_fit_derivatives(
                fit_bytes,
                activity_id,
                base_path,
                activity_type=activity_type,
            )
        )
        return uploaded

    if fit_bytes is None:
        return uploaded

    if ".fit" in only and not check_gcs_path_exists(
        export_blob_path(base_path, activity_id, ".fit")
    ):
        upload_to_gcs(
            fit_bytes,
            export_blob_path(base_path, activity_id, ".fit"),
            activity_id,
            "application/vnd.garmin.fit",
        )
        uploaded.append(".fit")

    if ".csv" in only and not check_gcs_path_exists(
        export_blob_path(base_path, activity_id, ".csv")
    ):
        lap_csv = fit_bytes_to_connect_lap_csv(fit_bytes, activity_type=activity_type)
        if lap_csv is not None and not lap_csv.empty:
            upload_to_gcs(
                lap_csv,
                export_blob_path(base_path, activity_id, ".csv"),
                activity_id,
                "text/csv",
            )
            uploaded.append(".csv")

    if ".gpx" in only and not check_gcs_path_exists(
        export_blob_path(base_path, activity_id, ".gpx")
    ):
        gpx_bytes = fit_bytes_to_gpx(fit_bytes)
        if gpx_bytes:
            upload_to_gcs(
                gpx_bytes,
                export_blob_path(base_path, activity_id, ".gpx"),
                activity_id,
                "application/gpx+xml",
            )
            uploaded.append(".gpx")

    return uploaded


def download_activity_exports(
    activity_id: int,
    client,
    base_path: str,
    *,
    only_extensions: Iterable[str] | None = None,
    activity_type: str | None = None,
) -> list[str]:
    """
    Download Garmin export formats and upload to GCS.
    Returns extensions successfully uploaded.
    """
    if is_personal_client(client):
        return backfill_personal_activity_exports(
            activity_id,
            client,
            base_path,
            only_extensions=only_extensions,
            activity_type=activity_type,
        )

    only = {e if e.startswith(".") else f".{e}" for e in only_extensions} if only_extensions else None
    uploaded: list[str] = []
    fmt_enum = client.ActivityDownloadFormat

    for fmt_name, ext, ctype in EXPORT_SPECS:
        if only is not None and ext not in only:
            continue
        gcs_path = export_blob_path(base_path, activity_id, ext)
        if check_gcs_path_exists(gcs_path):
            continue
        try:
            dl_fmt = getattr(fmt_enum, fmt_name)
            data = client.download_activity(activity_id, dl_fmt=dl_fmt)
            upload_to_gcs(data, gcs_path, activity_id, ctype)
            uploaded.append(ext)
        except Exception as e:
            logger.warning(
                "Format %s not available for activity %s: %s",
                ext,
                activity_id,
                e,
            )
    return uploaded
