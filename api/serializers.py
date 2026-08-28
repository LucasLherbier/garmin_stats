"""Convert pandas / numpy values to JSON-safe Python types."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    if isinstance(value, (np.floating, float)):
        v = float(value)
        return default if math.isnan(v) else v
    try:
        v = float(value)
        return default if math.isnan(v) else v
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    if value is None or pd.isna(value):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.floating, float)):
        if math.isnan(value):
            return None
        return float(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _serialize_value(v) for k, v in value.items()}
    if pd.isna(value):
        return None
    return value


def df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    records: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        records.append({str(k): _serialize_value(v) for k, v in row.items()})
    return records


def record_from_series(row: pd.Series) -> dict[str, Any]:
    return {str(k): _serialize_value(v) for k, v in row.items()}
