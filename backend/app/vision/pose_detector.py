"""
Pose Detector

MediaPipe Pose (BlazePose) landmark extraction, reduced to a small set of
clinically-relevant structured signals: posture (upright/hunched/guarding),
shoulder symmetry, and raw landmark points for downstream movement/pain
detectors. Free/local model, CPU-first (`model_complexity=0` = "Lite").
"""
import logging
from typing import Dict, Any, List, Tuple

import numpy as np

from app.vision.feature_extractor import euclidean, landmark_to_xy

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    mp = None
    MEDIAPIPE_AVAILABLE = False

# MediaPipe Pose landmark indices used here
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24
NOSE = 0


class PoseDetector:
    def __init__(self):
        self.available = False
        self._pose = None
        if MEDIAPIPE_AVAILABLE:
            try:
                self._pose = mp.solutions.pose.Pose(
                    static_image_mode=True, model_complexity=0, min_detection_confidence=0.5
                )
                self.available = True
            except Exception as e:
                logger.warning(f"PoseDetector: could not initialize MediaPipe Pose ({e}); disabled")

    def detect(self, rgb_frame: np.ndarray) -> Dict[str, Any]:
        if not self.available:
            return {"available": False}
        try:
            results = self._pose.process(rgb_frame)
            if not results.pose_landmarks:
                return {"available": True, "detected": False}

            lm = results.pose_landmarks.landmark
            left_shoulder = landmark_to_xy(lm[LEFT_SHOULDER])
            right_shoulder = landmark_to_xy(lm[RIGHT_SHOULDER])
            left_hip = landmark_to_xy(lm[LEFT_HIP])
            right_hip = landmark_to_xy(lm[RIGHT_HIP])
            nose = landmark_to_xy(lm[NOSE])

            shoulder_tilt = abs(left_shoulder[1] - right_shoulder[1])
            torso_height = euclidean(
                ((left_shoulder[0] + right_shoulder[0]) / 2, (left_shoulder[1] + right_shoulder[1]) / 2),
                ((left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2),
            )
            forward_lean = nose[1] > min(left_shoulder[1], right_shoulder[1])

            posture = "guarding_or_hunched" if (shoulder_tilt > 0.06 or torso_height < 0.18) else "neutral"

            landmarks_xy: List[Tuple[float, float]] = [landmark_to_xy(p) for p in lm]

            return {
                "available": True,
                "detected": True,
                "posture": posture,
                "shoulder_tilt": round(shoulder_tilt, 4),
                "torso_height": round(torso_height, 4),
                "forward_lean": bool(forward_lean),
                "landmarks_xy": landmarks_xy,
                "confidence": 0.7,
            }
        except Exception as e:
            logger.warning(f"PoseDetector: detection failed ({e})")
            return {"available": False, "error": str(e)}

    def close(self):
        if self._pose:
            try:
                self._pose.close()
            except Exception:
                pass
