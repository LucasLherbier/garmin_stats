import os
import io
import logging
import pandas as pd
from google.cloud import storage, bigquery
from google.cloud.exceptions import NotFound
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global variables for GCP
try:
    gcs_client = storage.Client()
    GCP_BUCKET_NAME = os.getenv('GCP_BUCKET_NAME')
    bucket = gcs_client.bucket(GCP_BUCKET_NAME) if GCP_BUCKET_NAME else None
    
    bq_client = bigquery.Client()
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', bq_client.project)
    GCP_DATASET_ID = os.getenv('GCP_DATASET_ID', 'garmin_stats')

except Exception as e:
    logger.error(f"Failed to initialize GCP clients: {e}")
    bucket = None
    bq_client = None

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
            
            # 2. Check for existence of current IDs
            # We use a parameterized query for efficiency and to avoid pulling the whole table
            ids_to_check = df['activityId'].astype(int).unique().tolist()

            query = f"SELECT activityId FROM `{table_id}` WHERE activityId IN UNNEST(@ids) LIMIT 1"
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("ids", "INT64", ids_to_check)
                ]
            )

            
            query_job = bq_client.query(query, job_config=job_config)
            results = query_job.result()

            # 3. If even ONE row is returned, stop and exit
            if results.total_rows > 0:
                logger.warning(f"Aborting upload: activityId(s) already exist in {table_name}.")
                return False 

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

def query_bigquery(query):
    """Execute a BigQuery query and return a pandas DataFrame."""
    if bq_client is None:
        logger.error("BigQuery client not initialized.")
        return pd.DataFrame()
    try:
        query_job = bq_client.query(query)
        return query_job.to_dataframe()
    except Exception as e:
        logger.error(f"BigQuery Query Error: {e}")
        return pd.DataFrame()




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


