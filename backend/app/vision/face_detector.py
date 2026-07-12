"""
Face Detector

MediaPipe FaceMesh landmark extraction. Publishes structured facial
geometry features (eyebrow/eye/mouth openness ratios) rather than raw
landmarks to the rest of the app - EmotionDetector and PainDetector both
consume this output instead of touching MediaPipe directly.
"""
import logging
from typing import Dict, Any

import numpy as np

from app.vision.feature_extractor import euclidean, landmark_to_xy

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    mp = None
    MEDIAPIPE_AVAILABLE = False

# Key FaceMesh landmark indices (468-point topology)
LEFT_EYE_TOP, LEFT_EYE_BOTTOM = 159, 145
RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM = 386, 374
MOUTH_TOP, MOUTH_BOTTOM = 13, 14
MOUTH_LEFT, MOUTH_RIGHT = 78, 308
LEFT_BROW, LEFT_EYE_CENTER = 105, 159
RIGHT_BROW, RIGHT_EYE_CENTER = 334, 386


class FaceDetector:
    def __init__(self):
        self.available = False
        self._mesh = None
        if MEDIAPIPE_AVAILABLE:
            try:
                self._mesh = mp.solutions.face_mesh.FaceMesh(
                    static_image_mode=True, max_num_faces=1, refine_landmarks=False,
                    min_detection_confidence=0.5,
                )
                self.available = True
            except Exception as e:
                logger.warning(f"FaceDetector: could not initialize MediaPipe FaceMesh ({e}); disabled")

    def detect(self, rgb_frame: np.ndarray) -> Dict[str, Any]:
        if not self.available:
            return {"available": False}
        try:
            results = self._mesh.process(rgb_frame)
            if not results.multi_face_landmarks:
                return {"available": True, "detected": False}

            lm = results.multi_face_landmarks[0].landmark

            eye_open_l = euclidean(landmark_to_xy(lm[LEFT_EYE_TOP]), landmark_to_xy(lm[LEFT_EYE_BOTTOM]))
            eye_open_r = euclidean(landmark_to_xy(lm[RIGHT_EYE_TOP]), landmark_to_xy(lm[RIGHT_EYE_BOTTOM]))
            mouth_open = euclidean(landmark_to_xy(lm[MOUTH_TOP]), landmark_to_xy(lm[MOUTH_BOTTOM]))
            mouth_width = euclidean(landmark_to_xy(lm[MOUTH_LEFT]), landmark_to_xy(lm[MOUTH_RIGHT]))
            brow_lower_l = euclidean(landmark_to_xy(lm[LEFT_BROW]), landmark_to_xy(lm[LEFT_EYE_CENTER]))
            brow_lower_r = euclidean(landmark_to_xy(lm[RIGHT_BROW]), landmark_to_xy(lm[RIGHT_EYE_CENTER]))

            return {
                "available": True,
                "detected": True,
                "eye_openness": round((eye_open_l + eye_open_r) / 2, 4),
                "mouth_openness": round(mouth_open, 4),
                "mouth_width": round(mouth_width, 4),
                "brow_lowering": round((brow_lower_l + brow_lower_r) / 2, 4),
                "confidence": 0.7,
            }
        except Exception as e:
            logger.warning(f"FaceDetector: detection failed ({e})")
            return {"available": False, "error": str(e)}

    def close(self):
        if self._mesh:
            try:
                self._mesh.close()
            except Exception:
                pass
