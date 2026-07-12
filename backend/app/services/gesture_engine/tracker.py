"""
GestureMed AI — Gesture Tracker Service
Manages per-consultation gesture engine instances and
streams results via Socket.IO to consultation rooms.
"""
import asyncio
import base64
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

from app.services.gesture_engine.recognizer import GestureEngine, GestureFrameResult
from app.services.gesture_engine.actions import PatientGestureActions, DoctorGestureActions

logger = logging.getLogger(__name__)

# Thread pool for blocking MediaPipe calls
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gesture_worker")


class ConsultationGestureSession:
    """
    Per-consultation gesture session.
    Owns a GestureEngine instance and role-specific action handler.
    """

    def __init__(self, consultation_id: str, user_role: str):
        self.consultation_id = consultation_id
        self.user_role = user_role
        self.engine = GestureEngine(max_num_hands=2, min_confidence=0.7)
        self.actions = (
            DoctorGestureActions()
            if user_role == "DOCTOR"
            else PatientGestureActions()
        )
        self.frame_count = 0
        self.last_gesture: Optional[str] = None

    def process_frame_sync(self, frame_bytes: bytes) -> GestureFrameResult:
        """Blocking call — run via executor."""
        self.frame_count += 1
        return self.engine.process_frame(frame_bytes)

    def close(self):
        self.engine.close()


class GestureTracker:
    """
    Global tracker that manages one ConsultationGestureSession per
    (consultation_id, user_id) pair. Thread-safe via asyncio.

    Usage:
        tracker = GestureTracker()
        session = tracker.get_or_create(consultation_id, user_id, role)
        result = await tracker.process_frame(session, frame_bytes)
    """

    def __init__(self):
        self._sessions: Dict[str, ConsultationGestureSession] = {}

    def _session_key(self, consultation_id: str, user_id: str) -> str:
        return f"{consultation_id}:{user_id}"

    def get_or_create(
        self, consultation_id: str, user_id: str, user_role: str
    ) -> ConsultationGestureSession:
        key = self._session_key(consultation_id, user_id)
        if key not in self._sessions:
            self._sessions[key] = ConsultationGestureSession(consultation_id, user_role)
            logger.info(f"Created gesture session: {key} role={user_role}")
        return self._sessions[key]

    async def process_frame(
        self, session: ConsultationGestureSession, frame_bytes: bytes
    ) -> GestureFrameResult:
        """Process a raw frame asynchronously via thread pool."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, session.process_frame_sync, frame_bytes
        )
        return result

    def close_session(self, consultation_id: str, user_id: str):
        key = self._session_key(consultation_id, user_id)
        session = self._sessions.pop(key, None)
        if session:
            session.close()
            logger.info(f"Closed gesture session: {key}")

    def close_all_for_consultation(self, consultation_id: str):
        keys_to_remove = [k for k in self._sessions if k.startswith(f"{consultation_id}:")]
        for key in keys_to_remove:
            session = self._sessions.pop(key)
            session.close()
            logger.info(f"Closed gesture session (consultation ended): {key}")


# Singleton tracker
gesture_tracker = GestureTracker()


async def process_gesture_frame_from_socket(
    consultation_id: str,
    user_id: str,
    user_role: str,
    frame_b64: str,
) -> dict:
    """
    High-level helper for the Socket.IO gesture_frame event handler.

    Accepts a base64-encoded JPEG/PNG frame, runs MediaPipe,
    maps to an action, and returns a dict ready to broadcast.
    """
    try:
        frame_bytes = base64.b64decode(frame_b64)
    except Exception as e:
        logger.warning(f"Invalid frame encoding: {e}")
        return {"error": "invalid_frame"}

    session = gesture_tracker.get_or_create(consultation_id, user_id, user_role)
    result = await gesture_tracker.process_frame(session, frame_bytes)

    action_result = session.actions.handle(
        gesture=result.primary_gesture,
        metadata=result.metadata,
    )

    payload = {
        "gesture": result.primary_gesture,
        "confidence": result.confidence,
        "hands_detected": result.hands_detected,
        "metadata": result.metadata,
        "landmarks": result.landmarks_raw,
        "action": None,
    }

    if action_result:
        payload["action"] = {
            "type": action_result.action_type,
            "message": action_result.message,
            "level": action_result.notification_level,
            "metadata": action_result.metadata,
        }

    return payload
