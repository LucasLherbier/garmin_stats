"""FastAPI dependencies."""

from utils.utils_gcp import query_bigquery, query_bigquery_live


def get_query_fn():
    return query_bigquery


def get_live_query_fn():
    return query_bigquery_live
