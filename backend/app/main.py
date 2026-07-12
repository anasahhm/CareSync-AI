"""
GestureMed AI — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import auth, users, consultations, gestures, reports, annotations, agent_processing, demo, video, gpu, metrics, memory, rag
from app.core.socketio_app import sio
from app.services.agent_service import get_agent_service, shutdown_agent_registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup phase
    logger.info("CareSyncAI starting up...")
    
    # Ensure uploads directory exists
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    
    if settings.ENVIRONMENT == "development":
        # Create tables (Alembic handles migrations in prod)
        async with engine.begin() as conn:
        	await conn.run_sync(Base.metadata.create_all)
    
    # Initialize agent system
    try:
        await get_agent_service()
        logger.info("Agent system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent system: {e}")
        raise
    
    logger.info("CareSyncAI startup complete")
    
    yield
    
    # Shutdown phase
    logger.info("CareSyncAI shutting down...")
    try:
        await shutdown_agent_registry()
        logger.info("Agent system shutdown complete")
    except Exception as e:
        logger.error(f"Error during agent shutdown: {e}")
    
    await engine.dispose()
    logger.info("CareSyncAI shutdown complete")


def create_application() -> FastAPI:
    app = FastAPI(
        title="CareSyncAI - Band of Agents Healthcare Platform",
        description="Enterprise Multi-Agent Healthcare Coordination Platform",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── REST Routes ───────────────────────────────────────────────
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(consultations.router, prefix="/api/consultations", tags=["consultations"])
    app.include_router(agent_processing.router, prefix="/api/agents", tags=["agents"])
    app.include_router(demo.router, prefix="/api", tags=["demo"])
    app.include_router(gestures.router, prefix="/api/gestures", tags=["gestures"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
    app.include_router(annotations.router, prefix="/api/annotations", tags=["annotations"])
    app.include_router(video.router, prefix="/api/video", tags=["video"])
    app.include_router(gpu.router, prefix="/api/gpu", tags=["gpu"])
    app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
    app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
    app.include_router(rag.router, prefix="/api/rag", tags=["rag"])

    # ── Static Uploads ────────────────────────────────────────────
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

    # ── Health Check ──────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "caresyncai-band-of-agents"}

    return app


# Wrap with Socket.IO ASGI
fastapi_app = create_application()
app = socketio.ASGIApp(sio, fastapi_app)
