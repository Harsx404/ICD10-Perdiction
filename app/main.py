from contextlib import asynccontextmanager
from pathlib import Path
import threading

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "static" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import here to avoid circular imports; the pipeline singleton is already
    # created at import time inside analyze.py.
    from app.api.routes.analyze import pipeline

    def _warm_up():
        pipeline.icd_prediction_service.warm_up()

    thread = threading.Thread(target=_warm_up, daemon=True, name="icd-warm-up")
    thread.start()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Clinical text analysis and ICD-10 coding API.",
    lifespan=lifespan,
)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Serve the built React SPA from static/dist
if DIST_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="spa-assets")


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    if (DIST_DIR / "index.html").exists():
        return FileResponse(DIST_DIR / "index.html")  # type: ignore[return-value]
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "review": "/review",
    }


@app.get("/review", include_in_schema=False)
def review_page() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "review.html")


# SPA catch-all — serve index.html for client-side routes (billing, history)
@app.get("/{path:path}", include_in_schema=False)
def spa_catch_all(path: str):
    # Don't intercept API or static requests
    if path.startswith(("api/", "static/", "assets/", "docs", "redoc", "openapi.json")):
        return {"detail": "Not Found"}
    if DIST_DIR.is_dir() and (DIST_DIR / "index.html").exists():
        return FileResponse(DIST_DIR / "index.html")
    return {"detail": "Frontend not built. Run: cd frontend && npm run build"}
