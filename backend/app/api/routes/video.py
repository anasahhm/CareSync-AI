"""
CareSyncAI V2 — Video / Vision API

Single-frame upload endpoints for the vision pipeline (camera -> preprocessing
-> parallel detectors -> fusion -> observation). Streaming is intentionally
NOT implemented here (kept optional per spec) - the frontend posts frames
periodically (e.g. every 500ms-1s) to /video/frame instead, which is CPU-
friendly and avoids needing a persistent WebSocket video channel.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models import User
from app.services.agent_service import get_agent_service

logger = logging.getLogger(__name__)

router = APIRouter()


class VideoSessionRequest(BaseModel):
    consultation_id: str


@router.post("/start")
async def start_video_session(
    body: VideoSessionRequest,
    current_user: User = Depends(get_current_user),
):
    agent_service = await get_agent_service()
    if not agent_service.vision_manager:
        raise HTTPException(status_code=503, detail="Vision system not initialized")
    return agent_service.vision_manager.start_session(body.consultation_id)


@router.post("/stop")
async def stop_video_session(
    body: VideoSessionRequest,
    current_user: User = Depends(get_current_user),
):
    agent_service = await get_agent_service()
    if not agent_service.vision_manager:
        raise HTTPException(status_code=503, detail="Vision system not initialized")
    return agent_service.vision_manager.stop_session(body.consultation_id)


@router.post("/frame")
async def process_video_frame(
    consultation_id: str = Form(...),
    frame: UploadFile = File(...),
    annotation_x: Optional[float] = Form(None),
    annotation_y: Optional[float] = Form(None),
    current_user: User = Depends(get_current_user),
):
    agent_service = await get_agent_service()
    if not agent_service.vision_manager:
        raise HTTPException(status_code=503, detail="Vision system not initialized")

    frame_bytes = await frame.read()
    if not frame_bytes:
        raise HTTPException(status_code=400, detail="Empty frame upload")

    annotation_point = (annotation_x, annotation_y) if annotation_x is not None and annotation_y is not None else None

    observation = await agent_service.vision_manager.process_frame(
        consultation_id, frame_bytes, annotation_point=annotation_point
    )
    return observation


@router.get("/status/{consultation_id}")
async def get_video_status(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
):
    agent_service = await get_agent_service()
    if not agent_service.vision_manager:
        raise HTTPException(status_code=503, detail="Vision system not initialized")
    return agent_service.vision_manager.get_status(consultation_id)


@router.get("/results/{consultation_id}")
async def get_video_results(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
):
    agent_service = await get_agent_service()
    if not agent_service.vision_manager:
        raise HTTPException(status_code=503, detail="Vision system not initialized")
    observation = agent_service.vision_manager.get_latest_observation(consultation_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="No vision observation available yet for this consultation")
    return observation


@router.post("/audio")
async def process_audio_clip(
    consultation_id: str = Form(...),
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Optional companion endpoint: analyzes a short WAV clip for speech-emotion
    signal and merges it into the consultation's latest fused observation."""
    agent_service = await get_agent_service()
    if not agent_service.vision_manager:
        raise HTTPException(status_code=503, detail="Vision system not initialized")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    return await agent_service.vision_manager.analyze_speech(consultation_id, audio_bytes)
