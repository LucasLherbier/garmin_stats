"""Garmin Analytics — FastAPI backend for the mobile web app."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routes import overview, race, races, report, sports, stats
from api.routes import sync as sync_routes
from api.sync_scheduler import start_scheduler, stop_scheduler

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173"
)
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Garmin Analytics API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_cache_headers(request, call_next):
    """Let the browser reuse data GETs for a few minutes."""
    response = await call_next(request)
    path = request.url.path
    if (
        request.method == "GET"
        and path.startswith("/api/")
        and not path.startswith(("/api/sync", "/api/health", "/api/report/download"))
    ):
        response.headers["Cache-Control"] = (
            "private, max-age=300, stale-while-revalidate=600"
        )
    return response


app.include_router(overview.router, prefix="/api")
app.include_router(sports.router, prefix="/api")
app.include_router(races.router, prefix="/api")
app.include_router(race.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(sync_routes.router, prefix="/api")


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
