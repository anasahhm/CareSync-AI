"""
Pain Detector

Fuses facial-emotion signal, pose posture/movement (guarding/stillness),
and any doctor/patient-placed pointer annotations into a single
"pain_score" observation with a localized body region, matching the format
requested for medical observations:

    {"pain_score": 0.73, "body_part": "abdomen", "confidence": 0.91}

Reuses the existing, already-working `detect_body_region` mapping from
`app.services.gesture_engine.ai_annotations` instead of reimplementing body
region geometry.
"""
import logging
from typing import Dict, Any, Optional, Tuple

from app.services.gesture_engine.ai_annotations import detect_body_region

logger = logging.getLogger(__name__)

DISTRESS_EMOTIONS = {"distress_or_pain"}
GUARDING_POSTURES = {"guarding_or_hunched"}
STILL_CLASSIFICATIONS = {"still_or_guarding"}


class PainDetector:
    available = True

    def detect(
        self,
        emotion_result: Dict[str, Any],
        pose_result: Dict[str, Any],
        movement_result: Dict[str, Any],
        annotation_point: Optional[Tuple[float, float]] = None,
    ) -> Dict[str, Any]:
        signals = []
        weight_sum = 0.0
        score_sum = 0.0

        if emotion_result.get("available") and emotion_result.get("emotion") in DISTRESS_EMOTIONS:
            score_sum += emotion_result.get("confidence", 0.6) * 0.9
            weight_sum += emotion_result.get("confidence", 0.6)
            signals.append("facial_distress")

        if pose_result.get("available") and pose_result.get("detected") and pose_result.get("posture") in GUARDING_POSTURES:
            score_sum += pose_result.get("confidence", 0.6) * 0.8
            weight_sum += pose_result.get("confidence", 0.6)
            signals.append("guarding_posture")

        if movement_result.get("available") and movement_result.get("classification") in STILL_CLASSIFICATIONS:
            score_sum += 0.5 * 0.6
            weight_sum += 0.5
            signals.append("protective_stillness")

        if not signals:
            return {"available": True, "pain_score": 0.0, "body_part": None, "confidence": 0.3, "signals": []}

        pain_score = round(min(1.0, score_sum / max(weight_sum, 1e-6)), 2)

        body_part = None
        if annotation_point:
            body_part, _clinical_term = detect_body_region(*annotation_point)

        confidence = round(min(0.95, 0.4 + 0.15 * len(signals)), 2)

        return {
            "available": True,
            "pain_score": pain_score,
            "body_part": body_part,
            "confidence": confidence,
            "signals": signals,
        }
