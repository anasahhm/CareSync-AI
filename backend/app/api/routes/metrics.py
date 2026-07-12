"""
CareSyncAI V2 — Prometheus Metrics

Exposes /metrics in Prometheus text-exposition format. Deliberately not
behind auth (Prometheus scrapers don't send JWTs) - if this needs to be
locked down in production, put it behind network policy / nginx basic
auth in the reverse proxy layer, not application auth.
"""
import logging

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)
router = APIRouter()

CONSULTATION_REQUESTS = Counter(
    "caresyncai_consultation_requests_total", "Total consultations processed", ["status"]
)
AGENT_EXECUTION_DURATION = Histogram(
    "caresyncai_agent_execution_seconds", "Per-agent execution duration", ["agent_type"]
)
CONSENSUS_RISK_SCORE = Gauge(
    "caresyncai_last_consensus_risk_score", "Most recent consensus overall risk score"
)
ACTIVE_VISION_SESSIONS = Gauge(
    "caresyncai_active_vision_sessions", "Number of active vision (camera) sessions"
)
GPU_BACKEND_INFO = Gauge(
    "caresyncai_gpu_backend_info", "1 for the currently active GPU backend", ["backend"]
)


@router.get("", response_class=PlainTextResponse)
async def metrics():
    try:
        from app.services.agent_service import get_agent_service
        agent_service = await get_agent_service()
        if agent_service.vision_manager:
            ACTIVE_VISION_SESSIONS.set(agent_service.vision_manager.camera_manager.active_session_count())
        if agent_service.gpu_manager:
            info = agent_service.gpu_manager.device_manager.info()
            GPU_BACKEND_INFO.labels(backend=info["backend"]).set(1)
    except Exception as e:
        logger.debug(f"metrics: could not refresh live gauges (non-fatal): {e}")

    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
