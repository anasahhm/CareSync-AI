"""
Movement Detector

Frame-to-frame movement analysis from pose landmarks (no optical flow
needed - landmark displacement is cheaper and already normalized). Detects
large sudden movement (distress/agitation signal) vs. very low movement
(guarding/stillness, itself a pain indicator) using a rolling window kept
by CameraManager.
"""
import logging
from typing import Dict, Any, List, Tuple, Optional

from app.vision.feature_extractor import landmark_displacement

logger = logging.getLogger(__name__)

HIGH_MOVEMENT_THRESHOLD = 0.05
LOW_MOVEMENT_THRESHOLD = 0.002


class MovementDetector:
    available = True  # pure geometry, no external model dependency

    def detect(
        self,
        prev_landmarks: Optional[List[Tuple[float, float]]],
        curr_landmarks: Optional[List[Tuple[float, float]]],
    ) -> Dict[str, Any]:
        if not curr_landmarks:
            return {"available": False}
        if not prev_landmarks:
            return {"available": True, "movement_magnitude": 0.0, "classification": "insufficient_history"}

        magnitude = landmark_displacement(prev_landmarks, curr_landmarks)

        if magnitude > HIGH_MOVEMENT_THRESHOLD:
            classification = "agitated_or_distressed"
        elif magnitude < LOW_MOVEMENT_THRESHOLD:
            classification = "still_or_guarding"
        else:
            classification = "normal"

        return {
            "available": True,
            "movement_magnitude": round(magnitude, 5),
            "classification": classification,
        }
