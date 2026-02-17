
from google.cloud import bigquery
import os
from dotenv import load_dotenv

load_dotenv()

client = bigquery.Client()
dataset_id = os.getenv('GCP_DATASET_ID', 'garmin_stats_db')

# If dataset_id has project.dataset, we need to split it for list_tables if we use dataset_ref
# Or just use the string dataset_id

print(f"Listing tables for dataset: {dataset_id}")
tables = client.list_tables(dataset_id)

print(f"Tables:")
for table in tables:
    print(table.table_id)
