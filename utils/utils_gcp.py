import os
import io
import logging
import secrets
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
import pandas as pd
from google.cloud import storage, bigquery
from google.cloud.exceptions import NotFound
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

import json
from google.oauth2 import service_account

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from repo root (works regardless of process cwd)
load_dotenv(_PROJECT_ROOT / ".env")

# Global variables for GCP
gcs_client = None
bq_client = None
bucket = None
_gcs_credentials = None
REPORT_SHARE_EXPIRY_DAYS = int(os.getenv("REPORT_SHARE_EXPIRY_DAYS", "7"))
# GCS V4 signed URLs with service-account keys are capped at 7 days.
GCS_SIGNED_URL_MAX_DAYS = 7
REPORT_PUBLIC_BASE_URL = os.getenv(
    "REPORT_PUBLIC_BASE_URL",
    "https://garmin-stats-three.vercel.app/api/report",
).rstrip("/")
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', '').strip('"').strip("'") or None
GCP_DATASET_ID = os.getenv('GCP_DATASET_ID', 'garmin_stats').strip('"').strip("'")
GCP_BUCKET_NAME = os.getenv('GCP_BUCKET_NAME', '').strip('"').strip("'") or None


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str.strip('"').strip("'"))
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    root_path = _PROJECT_ROOT / path
    if root_path.exists():
        return root_path
    return path

def initialize_clients():
    global gcs_client, bq_client, bucket, GCP_PROJECT_ID, _gcs_credentials
    
    try:
        credentials = None
        # Priority 1: GOOGLE_CREDENTIALS_JSON (env var string - best for Render/Docker)
        credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip('"').strip("'")
        if credentials_json:
            try:
                info = json.loads(credentials_json)
                credentials = service_account.Credentials.from_service_account_info(info)
                if not GCP_PROJECT_ID:
                    GCP_PROJECT_ID = info.get('project_id')
                logger.info("GCP Clients: Using credentials from GOOGLE_CREDENTIALS_JSON")
            except Exception as e:
                logger.error(f"Failed to parse GOOGLE_CREDENTIALS_JSON (checking if it is raw JSON or a path): {e}")

        # Priority 2: credentials.json (local file)
        if not credentials:
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json').strip('"').strip("'")
            resolved_cred = _resolve_path(cred_path)
            if resolved_cred.exists():
                credentials = service_account.Credentials.from_service_account_file(str(resolved_cred))
                if not GCP_PROJECT_ID:
                    GCP_PROJECT_ID = credentials.project_id
                logger.info(f"GCP Clients: Using credentials from file {resolved_cred}")

        # Initialize clients
        if credentials:
            _gcs_credentials = credentials
            gcs_client = storage.Client(credentials=credentials, project=GCP_PROJECT_ID)
            bq_client = bigquery.Client(credentials=credentials, project=GCP_PROJECT_ID)
        else:
            # Fallback to default credentials (if running on GCP environment or env var set)
            gcs_client = storage.Client()
            bq_client = bigquery.Client()
            logger.info("GCP Clients: Using default credentials")
            try:
                _gcs_credentials = gcs_client._credentials
            except Exception:
                _gcs_credentials = None

        if gcs_client and GCP_BUCKET_NAME:
            bucket = gcs_client.bucket(GCP_BUCKET_NAME)
        
        if bq_client and not GCP_PROJECT_ID:
            GCP_PROJECT_ID = bq_client.project

    except Exception as e:
        logger.error(f"Failed to initialize GCP clients: {e}")
        # Keep clients as None to trigger warnings in UI

initialize_clients()

def upload_to_bigquery(df, table_name):
    """Checks if any activityId exists. If yes, exits. If no, uploads everything."""
    if bq_client is None or df.empty:
        logger.warning("Client not initialized or DataFrame is empty.")
        return False

    try:
        # Construct Table ID
        table_id = f"{GCP_PROJECT_ID}.{GCP_DATASET_ID}.{table_name}"
        if "." in GCP_DATASET_ID:
            table_id = GCP_DATASET_ID if table_name in GCP_DATASET_ID else f"{GCP_DATASET_ID}.{table_name}"

        try:
            # 1. Check if table exists
            bq_client.get_table(table_id)
            
            # 2. Check for existing IDs to filter them out
            ids_to_check = df['activityId'].astype(int).unique().tolist()

            query = f"SELECT DISTINCT activityId FROM `{table_id}` WHERE activityId IN UNNEST(@ids)"
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("ids", "INT64", ids_to_check)
                ]
            )

            query_job = bq_client.query(query, job_config=job_config)
            existing_ids = {int(row.activityId) for row in query_job.result()}

            # 3. Filter the DataFrame to keep only new IDs
            original_count = len(df)
            df = df[~df['activityId'].astype(int).isin(existing_ids)]

            if df.empty:
                logger.info(f"All {original_count} activities already exist in {table_name}. Skipping upload.")
                return True
            
            logger.info(f"Found {len(df)} new activities (out of {original_count}) to upload to {table_name}.")

        except NotFound:
            logger.info(f"Table {table_id} not found. It will be created on upload.")

        # 4. Upload full DataFrame if no duplicates were found
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        )
        job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()

        
        logger.info(f"Successfully uploaded {len(df)} rows to {table_id}")
        return True

    except Exception as e:
        logger.error(f"BigQuery Error: {e}")
        return False


def _table_id(table_name: str) -> str:
    table_id = f"{GCP_PROJECT_ID}.{GCP_DATASET_ID}.{table_name}"
    if "." in GCP_DATASET_ID:
        table_id = GCP_DATASET_ID if table_name in GCP_DATASET_ID else f"{GCP_DATASET_ID}.{table_name}"
    return table_id


DAILY_WELLNESS_SCHEMA = [
    bigquery.SchemaField("day", "DATE"),
    bigquery.SchemaField("sleep_score", "INT64"),
    bigquery.SchemaField("sleep_duration_sec", "INT64"),
    bigquery.SchemaField("sleep_deep_sec", "INT64"),
    bigquery.SchemaField("sleep_light_sec", "INT64"),
    bigquery.SchemaField("sleep_rem_sec", "INT64"),
    bigquery.SchemaField("sleep_awake_sec", "INT64"),
    bigquery.SchemaField("hrv_last_night_avg", "FLOAT64"),
    bigquery.SchemaField("hrv_status", "STRING"),
    bigquery.SchemaField("hrv_weekly_avg", "FLOAT64"),
    bigquery.SchemaField("resting_hr", "INT64"),
    bigquery.SchemaField("daily_steps", "INT64"),
    bigquery.SchemaField("daily_calories", "INT64"),
    bigquery.SchemaField("body_battery_high", "INT64"),
    bigquery.SchemaField("body_battery_low", "INT64"),
    bigquery.SchemaField("avg_stress", "INT64"),
    bigquery.SchemaField("activity_count", "INT64"),
    bigquery.SchemaField("total_duration_sec", "INT64"),
    bigquery.SchemaField("total_calories", "INT64"),
    bigquery.SchemaField("swim_distance_km", "FLOAT64"),
    bigquery.SchemaField("bike_distance_km", "FLOAT64"),
    bigquery.SchemaField("run_distance_km", "FLOAT64"),
    bigquery.SchemaField("elevation_gain_m", "FLOAT64"),
    bigquery.SchemaField("extract_status", "STRING"),
    bigquery.SchemaField("extract_errors", "STRING"),
    bigquery.SchemaField("extracted_at", "TIMESTAMP"),
]

_DAILY_WELLNESS_INT_COLS = [
    field.name for field in DAILY_WELLNESS_SCHEMA if field.field_type == "INT64"
]
_DAILY_WELLNESS_FLOAT_COLS = [
    field.name for field in DAILY_WELLNESS_SCHEMA if field.field_type == "FLOAT64"
]


def _prepare_daily_wellness_df(df: pd.DataFrame) -> pd.DataFrame:
    upload_df = df.copy()
    upload_df["day"] = pd.to_datetime(upload_df["day"], errors="coerce").dt.date

    for col in _DAILY_WELLNESS_INT_COLS:
        if col not in upload_df.columns:
            continue
        upload_df[col] = pd.to_numeric(upload_df[col], errors="coerce").apply(
            lambda value: None if pd.isna(value) else int(value)
        )

    for col in _DAILY_WELLNESS_FLOAT_COLS:
        if col not in upload_df.columns:
            continue
        upload_df[col] = pd.to_numeric(upload_df[col], errors="coerce").astype(float)

    if "extracted_at" in upload_df.columns:
        upload_df["extracted_at"] = pd.to_datetime(upload_df["extracted_at"], errors="coerce", utc=True)

    schema_cols = [field.name for field in DAILY_WELLNESS_SCHEMA]
    for col in schema_cols:
        if col not in upload_df.columns:
            upload_df[col] = None
    extra_cols = [col for col in upload_df.columns if col not in schema_cols]
    return upload_df[schema_cols + extra_cols]


def drop_daily_wellness_table(table_name: str = "daily_wellness") -> bool:
    if bq_client is None:
        logger.warning("Client not initialized.")
        return False
    try:
        table_id = _table_id(table_name)
        bq_client.delete_table(table_id, not_found_ok=True)
        logger.info("Dropped table %s.", table_id)
        return True
    except Exception as e:
        logger.error("Failed to drop daily_wellness table: %s", e)
        return False


def merge_daily_wellness_to_bigquery(df: pd.DataFrame, table_name: str = "daily_wellness") -> bool:
    """Upsert daily wellness rows keyed by calendar day."""
    if bq_client is None or df.empty:
        logger.warning("Client not initialized or DataFrame is empty.")
        return False

    try:
        table_id = _table_id(table_name)
        upload_df = _prepare_daily_wellness_df(df)

        days = sorted({str(day)[:10] for day in upload_df["day"].dropna().tolist()})
        delete_query = f"DELETE FROM `{table_id}` WHERE CAST(day AS STRING) IN UNNEST(@days)"
        delete_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ArrayQueryParameter("days", "STRING", days)]
        )
        try:
            bq_client.get_table(table_id)
            bq_client.query(delete_query, job_config=delete_config).result()
            logger.info("Removed %s existing daily_wellness row(s) before upsert.", len(days))
        except NotFound:
            logger.info("Table %s not found. It will be created on upload.", table_id)

        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            schema=DAILY_WELLNESS_SCHEMA,
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        )
        job = bq_client.load_table_from_dataframe(upload_df, table_id, job_config=job_config)
        job.result()
        logger.info("Upserted %s row(s) into %s.", len(upload_df), table_id)
        return True
    except Exception as e:
        logger.error(f"Daily wellness BigQuery Error: {e}")
        return False

def log_to_bigquery(activity_id, name_file, path_file, status):
    """Log activity processing status to BigQuery 'logs' table using MERGE (UPSERT)."""
    if bq_client is None:
        return False
    try:
        table_id = f"{GCP_PROJECT_ID}.{GCP_DATASET_ID}.logs"
        if "." in GCP_DATASET_ID:
             table_id = f"{GCP_DATASET_ID}.logs"
        
        # 1. Ensure the table exists with a schema (BigQuery MERGE needs a schema)
        schema = [
            bigquery.SchemaField("activity_id", "STRING"),
            bigquery.SchemaField("name_file", "STRING"),
            bigquery.SchemaField("path_file", "STRING"),
            bigquery.SchemaField("date", "STRING"),
            bigquery.SchemaField("status", "STRING"),
        ]
        try:
            table = bq_client.get_table(table_id)
            if not table.schema:
                logger.info(f"Existing table {table_id} has no schema. Updating it...")
                table.schema = schema
                bq_client.update_table(table, ["schema"])
        except NotFound:
            logger.info(f"Creating logs table: {table_id}")
            table = bigquery.Table(table_id, schema=schema)
            bq_client.create_table(table)
             
        # 2. Using MERGE for "Insert or Update" logic

        query = f"""
        MERGE `{table_id}` T
        USING (SELECT @activity_id AS activity_id, @name_file AS name_file) S
        ON T.activity_id = S.activity_id AND T.name_file = S.name_file
        WHEN MATCHED THEN
          UPDATE SET path_file = @path_file, date = @date, status = @status
        WHEN NOT MATCHED THEN
          INSERT (activity_id, name_file, path_file, date, status)
          VALUES (@activity_id, @name_file, @path_file, @date, @status)
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("activity_id", "STRING", str(activity_id)),
                bigquery.ScalarQueryParameter("name_file", "STRING", name_file),
                bigquery.ScalarQueryParameter("path_file", "STRING", path_file),
                bigquery.ScalarQueryParameter("date", "STRING", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")),
                bigquery.ScalarQueryParameter("status", "STRING", status),
            ]
        )
        
        query_job = bq_client.query(query, job_config=job_config)
        query_job.result()
        return True
    except Exception as e:
        # Simplify the error message to avoid technical metadata noise and long URLs
        msg = str(e)
        if "GET https://" in msg:
            msg = msg.split(": ", 1)[-1]  # Get the part after the URL
        msg = msg.split(';')[0]  # Get the part before any semicolons/job IDs
        logger.error(f"BigQuery Log Error: {msg}")
        return False

def _run_bigquery(query):
    if bq_client is None:
        logger.error("BigQuery client not initialized.")
        return pd.DataFrame()
    try:
        query_job = bq_client.query(query)
        return query_job.to_dataframe()
    except Exception as e:
        logger.error(f"BigQuery Query Error: {e}")
        return pd.DataFrame()


@lru_cache(maxsize=64)
def query_bigquery(query: str):
    """Execute a BigQuery query and return a pandas DataFrame (cached by query text)."""
    return _run_bigquery(query)


def query_bigquery_live(query: str):
    """Uncached BigQuery query (e.g. workout_summaries after backfill)."""
    return _run_bigquery(query)




def publish_report_html(html: str, activity_id: int, date_str: str) -> tuple[str | None, int]:
    """Upload an activity HTML report and return a short public share URL."""
    expiry_days = min(REPORT_SHARE_EXPIRY_DAYS, GCS_SIGNED_URL_MAX_DAYS)
    if bucket is None:
        logger.warning("Bucket not initialized. Cannot publish report.")
        return None, expiry_days

    token = secrets.token_urlsafe(8)
    share_path = f"reports/share/{token}.html"
    archive_path = f"reports/{activity_id}/report_{date_str}.html"

    try:
        for gcs_path in (share_path, archive_path):
            blob = bucket.blob(gcs_path)
            blob.upload_from_string(html, content_type="text/html; charset=utf-8")
            blob.cache_control = "public, max-age=3600"
            blob.patch()
        return f"{REPORT_PUBLIC_BASE_URL}/r/{token}", expiry_days
    except Exception as e:
        logger.error(f"Failed to publish report HTML: {e}")
        return None, expiry_days


def read_shared_report_html(token: str) -> str | None:
    """Load a published report HTML by its short share token."""
    if not bucket or not token or "/" in token or ".." in token:
        return None
    gcs_path = f"reports/share/{token}.html"
    try:
        if not check_gcs_path_exists(gcs_path):
            return None
        return bucket.blob(gcs_path).download_as_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read shared report {token}: {e}")
        return None


def save_to_gcs(data, gcs_path, content_type='application/octet-stream'):
    """Upload data (bytes or str) to GCS bucket."""
    if bucket is None:
        logger.warning(f"Bucket not initialized. Cannot save to {gcs_path}")
        return False
    try:
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(data, content_type=content_type)
        return True
    except Exception as e:
        logger.error(f"Erreur GCS (save): {e}")
        return False

def check_gcs_path_exists(gcs_path):
    """Check if a path exists in GCS bucket."""
    if not bucket: return False
    try:
        return bucket.blob(gcs_path).exists()
    except Exception as e:
        logger.error(f"Erreur GCS (exists): {e}")
        return False

def read_csv_from_gcs(gcs_path):
    """Read a CSV file from GCS bucket into a pandas DataFrame."""
    if not bucket: return None
    try:
        data = bucket.blob(gcs_path).download_as_string()
        return pd.read_csv(io.StringIO(data.decode('utf-8')))
    except Exception as e:
        logger.error(f"Erreur GCS (read): {e}")
        return None

def upload_to_gcs(data, gcs_path, activity_id, content_type='application/octet-stream'):
    """
    Unified function to upload data (DataFrame, str, or bytes) to GCS 
    and log the processing status to the BigQuery 'logs' table.
    """
    if isinstance(data, pd.DataFrame):
        payload = data.to_csv(index=False)
        content_type = 'text/csv'
    else:
        payload = data
        
    success = save_to_gcs(payload, gcs_path, content_type)
    
    # Log to BigQuery
    status = "PASSED" if success else "FAILED"
    file_name = os.path.basename(gcs_path)
    log_to_bigquery(activity_id, file_name, gcs_path, status)
    
    if success:
        logger.info(f"Successfully uploaded to GCS: {gcs_path}")
    else:
        logger.error(f"Failed upload to GCS: {gcs_path}")
        
    return success


