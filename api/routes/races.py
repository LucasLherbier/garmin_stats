from fastapi import APIRouter, Depends

from api.deps import get_query_fn
from api.serializers import df_to_records
from utils import sql_queries as sql

router = APIRouter(prefix="/races", tags=["races"])


@router.get("/results")
def race_results(query=Depends(get_query_fn)):
    df = query(sql.get_all_races_query()).fillna("")
    tri = df[df["sport"].str.contains("Triathlon", case=False, na=False)]
    running = df[df["sport"].str.contains("Running|Trail", case=False, na=False)]
    return {
        "triathlon": df_to_records(tri),
        "running": df_to_records(running),
    }
