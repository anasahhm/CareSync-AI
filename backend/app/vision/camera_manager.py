"""
Camera Manager

Owns per-consultation vision session state: the stateful MediaPipe detector
instances (gesture/pose/face graphs are expensive to construct - one per
consultation, reused across frames) and a short rolling history of pose
landmarks used by MovementDetector for frame-to-frame comparison.

Frames arrive over REST (single-frame uploads, see /api/video routes) or
optionally a stream; either way they funnel through the same per-session
state here rather than one-shot detector construction per request.
"""
import logging
import time
from typing import Dict, Optional, List, Tuple

from app.vision.gesture_detector import GestureDetector
from app.vision.pose_detector import PoseDetector
from app.vision.face_detector import FaceDetector

logger = logging.getLogger(__name__)

SESSION_IDLE_TIMEOUT_SECONDS = 600


class VisionSession:
    def __init__(self, consultation_id: str):
        self.consultation_id = consultation_id
        self.gesture_detector = GestureDetector()
        self.pose_detector = PoseDetector()
        self.face_detector = FaceDetector()
        self.last_pose_landmarks: Optional[List[Tuple[float, float]]] = None
        self.frame_count = 0
        self.last_seen = time.time()

    def touch(self):
        self.last_seen = time.time()

    def is_idle(self) -> bool:
        return (time.time() - self.last_seen) > SESSION_IDLE_TIMEOUT_SECONDS

    def close(self):
        self.gesture_detector.close()
        self.pose_detector.close()
        self.face_detector.close()


class CameraManager:
    """Process-local registry of active vision sessions, one per consultation."""

    def __init__(self):
        self._sessions: Dict[str, VisionSession] = {}

    def get_or_create(self, consultation_id: str) -> VisionSession:
        session = self._sessions.get(consultation_id)
        if session is None:
            session = VisionSession(consultation_id)
            self._sessions[consultation_id] = session
            logger.info(f"CameraManager: created vision session for {consultation_id}")
        session.touch()
        return session

    def get(self, consultation_id: str) -> Optional[VisionSession]:
        return self._sessions.get(consultation_id)

    def close_session(self, consultation_id: str) -> bool:
        session = self._sessions.pop(consultation_id, None)
        if session:
            session.close()
            return True
        return False

    def cleanup_idle_sessions(self) -> int:
        idle_ids = [cid for cid, s in self._sessions.items() if s.is_idle()]
        for cid in idle_ids:
            self.close_session(cid)
        return len(idle_ids)

    def active_session_count(self) -> int:
        return len(self._sessions)
