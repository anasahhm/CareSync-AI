"""
Multimodal Fusion

Combines the per-modality detector outputs (gesture, pose, face, emotion,
movement, pain, speech) into one structured "VisionObservation" - the only
shape agents and the consensus engine actually consume. Individual raw
detector payloads are kept under `modalities` for debugging/dashboard use,
but `summary` is what downstream reasoning should read.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MultimodalFusion:
    @staticmethod
    def fuse(
        consultation_id: str,
        gesture: Dict[str, Any],
        pose: Dict[str, Any],
        face: Dict[str, Any],
        emotion: Dict[str, Any],
        movement: Dict[str, Any],
        pain: Dict[str, Any],
        speech: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        speech = speech or {"available": False}

        active_modalities = [
            name for name, result in [
                ("gesture", gesture), ("pose", pose), ("face", face),
                ("emotion", emotion), ("movement", movement), ("pain", pain), ("speech", speech),
            ] if result.get("available")
        ]

        # Overall confidence: mean of whichever modalities actually produced
        # a confidence value, weighted down if few modalities are active
        confidences = [
            r.get("confidence") for r in [gesture, pose, face, emotion, movement, pain, speech]
            if r.get("available") and isinstance(r.get("confidence"), (int, float))
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        coverage_penalty = min(1.0, len(active_modalities) / 4)
        overall_confidence = round(avg_confidence * coverage_penalty, 3) if confidences else 0.0

        distress_flags = []
        if emotion.get("emotion") in ("distress_or_pain",):
            distress_flags.append("facial_distress")
        if pose.get("posture") == "guarding_or_hunched":
            distress_flags.append("guarding_posture")
        if movement.get("classification") == "agitated_or_distressed":
            distress_flags.append("agitated_movement")
        if speech.get("emotion") == "distressed_or_urgent":
            distress_flags.append("distressed_speech")

        summary = {
            "pain_score": pain.get("pain_score", 0.0),
            "body_part": pain.get("body_part"),
            "confidence": overall_confidence,
            "distress_flags": distress_flags,
            "primary_gesture": gesture.get("primary_gesture") if gesture.get("available") else None,
            "emotion": emotion.get("emotion") if emotion.get("available") else None,
            "posture": pose.get("posture") if pose.get("available") and pose.get("detected") else None,
            "movement": movement.get("classification") if movement.get("available") else None,
            "speech_emotion": speech.get("emotion") if speech.get("available") else None,
        }

        return {
            "consultation_id": consultation_id,
            "summary": summary,
            "active_modalities": active_modalities,
            "modalities": {
                "gesture": gesture, "pose": pose, "face": face,
                "emotion": emotion, "movement": movement, "pain": pain, "speech": speech,
            },
        }
