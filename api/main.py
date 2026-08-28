"""Garmin Analytics — FastAPI backend for the mobile web app."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import overview, race, races, report, sports, stats

app = FastAPI(
    title="Garmin Analytics API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router, prefix="/api")
app.include_router(sports.router, prefix="/api")
app.include_router(races.router, prefix="/api")
app.include_router(race.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(report.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve built React app in production (optional)
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
