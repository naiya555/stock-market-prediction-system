"""API Routes Package for Phase 13 FastAPI REST API."""

from fastapi import APIRouter

from app.api.routes.events import router as events_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.predict import router as predict_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(predict_router, prefix="/predict", tags=["prediction"])
api_router.include_router(history_router, prefix="/history", tags=["history"])
api_router.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
api_router.include_router(events_router, prefix="/events", tags=["events"])

__all__ = ["api_router"]
