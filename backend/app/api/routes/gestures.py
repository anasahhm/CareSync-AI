"""GestureMed AI — Gesture Events API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, GestureEvent

router = APIRouter()


class LogGestureRequest(BaseModel):
    consultation_id: str
    gesture_type: str
    confidence: float
    action_taken: Optional[str] = None
    metadata: dict = {}


@router.post("/log", status_code=201)
async def log_gesture(
    body: LogGestureRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = GestureEvent(
        consultation_id=body.consultation_id,
        user_id=current_user.id,
        gesture_type=body.gesture_type,
        confidence=body.confidence,
        action_taken=body.action_taken,
        metadata=body.metadata,
    )
    db.add(event)
    await db.commit()
    return {"status": "logged"}


@router.get("/{consultation_id}")
async def get_gestures(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GestureEvent)
        .where(GestureEvent.consultation_id == consultation_id)
        .order_by(GestureEvent.timestamp)
    )
    events = result.scalars().all()
    return [
        {
            "gesture_type": e.gesture_type,
            "confidence": e.confidence,
            "action_taken": e.action_taken,
            "timestamp": e.timestamp,
        }
        for e in events
    ]
