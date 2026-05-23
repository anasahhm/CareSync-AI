"""
Emotion Detector

Heuristic facial-expression classification from FaceDetector's geometry
features. Deliberately not a deep emotion-classification model (keeps this
CPU-cheap and dependency-free) - thresholds are calibrated to be
conservative: "neutral" is the default and a specific emotion is only
reported when its signature geometry is clearly present.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Approximate normalized-coordinate thresholds tuned for MediaPipe FaceMesh output
MOUTH_OPEN_THRESHOLD = 0.03
BROW_LOWER_THRESHOLD = 0.03
WIDE_MOUTH_RATIO_THRESHOLD = 0.45


class EmotionDetector:
    available = True  # pure heuristic, no external model to fail to load

    def detect(self, face_features: Dict[str, Any]) -> Dict[str, Any]:
        if not face_features.get("available") or not face_features.get("detected"):
            return {"available": False}

        mouth_openness = face_features.get("mouth_openness", 0.0)
        mouth_width = face_features.get("mouth_width", 0.0)
        brow_lowering = face_features.get("brow_lowering", 0.0)
        eye_openness = face_features.get("eye_openness", 0.0)

        mouth_ratio = (mouth_width / mouth_openness) if mouth_openness > 1e-6 else 999

        emotion = "neutral"
        confidence = 0.5

        if brow_lowering < BROW_LOWER_THRESHOLD and mouth_openness > MOUTH_OPEN_THRESHOLD:
            emotion = "distress_or_pain"
            confidence = 0.65
        elif mouth_ratio < WIDE_MOUTH_RATIO_THRESHOLD and mouth_openness > MOUTH_OPEN_THRESHOLD * 1.5:
            emotion = "distress_or_pain"
            confidence = 0.6
        elif eye_openness < 0.01 and mouth_openness < 0.01:
            emotion = "withdrawn_or_fatigued"
            confidence = 0.5
        elif mouth_openness < MOUTH_OPEN_THRESHOLD and brow_lowering >= BROW_LOWER_THRESHOLD:
            emotion = "calm"
            confidence = 0.55

        return {"available": True, "emotion": emotion, "confidence": confidence}
