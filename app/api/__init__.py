"""FastAPI Application and REST API Package for Phase 13.

Provides RESTful endpoints for directional prediction inference, multi-agent ensemble
synthesis, immutable prediction history, feedback handling, and macroeconomic events.
"""

from app.api.app import app, create_app
from app.api.routes import api_router

__all__ = [
    "api_router",
    "app",
    "create_app",
]
