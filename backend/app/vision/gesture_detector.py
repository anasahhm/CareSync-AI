"""
Gesture Detector

Thin adapter over the existing, already-working
`app.services.gesture_engine.recognizer.GestureEngine` (MediaPipe Hands).
Does NOT reimplement hand-landmark logic - it wraps the existing engine and
converts its output into the structured-observation shape the rest of the
vision pipeline uses, so gesture data flows through the same fusion path as
every other detector.
"""
import logging
from typing import Optional, Dict, Any

from app.services.gesture_engine.recognizer import GestureEngine

logger = logging.getLogger(__name__)


class GestureDetector:
    """Stateful per-session wrapper (one MediaPipe Hands graph per consultation)."""

    def __init__(self):
        self._engine: Optional[GestureEngine] = None
        try:
            self._engine = GestureEngine(max_num_hands=2, min_confidence=0.6)
            self.available = True
        except Exception as e:
            logger.warning(f"GestureDetector: could not initialize GestureEngine ({e}); gesture detection disabled")
            self.available = False

    def detect(self, frame_bytes: bytes) -> Dict[str, Any]:
        if not self.available:
            return {"available": False}
        try:
            result = self._engine.process_frame(frame_bytes)
            return {
                "available": True,
                "hands_detected": result.hands_detected,
                "primary_gesture": result.primary_gesture,
                "confidence": result.confidence,
                "metadata": result.metadata,
            }
        except Exception as e:
            logger.warning(f"GestureDetector: frame processing failed ({e})")
            return {"available": False, "error": str(e)}

    def close(self):
        if self._engine:
            try:
                self._engine.close()
            except Exception:
                pass
