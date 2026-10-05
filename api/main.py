"""Garmin Analytics — FastAPI backend for the mobile web app."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routes import overview, race, races, report, sports, stats

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173,"
    "https://garmin-stats-three.vercel.app"
)
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app = FastAPI(
    title="Garmin Analytics API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
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


# Serve built React app in production (optional). Explicit SPA fallback so deep links
# like /race/<slug> return index.html (StaticFiles html=True alone missed some paths).
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _register_frontend(dist: Path) -> None:
    root = dist.resolve()
    index = root / "index.html"
    if not index.is_file():
        return

    @app.get("/", include_in_schema=False)
    async def spa_index() -> FileResponse:
        return FileResponse(index)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (root / full_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


if _frontend_dist.exists():
    _register_frontend(_frontend_dist)
