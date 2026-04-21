from fastapi import APIRouter

from app.api.routes.analyze import router as analyze_router
from app.api.routes.billing import router as billing_router
from app.api.routes.health import router as health_router
from app.api.routes.meta import router as meta_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(analyze_router)
api_router.include_router(billing_router)
api_router.include_router(meta_router)
