"""
Frame Pipeline

camera -> preprocessing -> parallel detectors -> fusion -> observation.

MediaPipe/OpenCV calls are blocking (C++ under the hood), so they run in a
shared thread pool via `asyncio.to_thread` rather than blocking the event
loop - the same pattern the existing gesture tracker already uses.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from app.vision.preprocessing import preprocess
from app.vision.camera_manager import VisionSession
from app.vision.emotion_detector import EmotionDetector
from app.vision.movement_detector import MovementDetector
from app.vision.pain_detector import PainDetector
from app.vision.multimodal_fusion import MultimodalFusion

logger = logging.getLogger(__name__)

_emotion_detector = EmotionDetector()
_movement_detector = MovementDetector()
_pain_detector = PainDetector()


class FramePipeline:
    @staticmethod
    async def process(
        session: VisionSession,
        frame_bytes: bytes,
        annotation_point: Optional[tuple] = None,
    ) -> Dict[str, Any]:
        preprocessed = await asyncio.to_thread(preprocess, frame_bytes)
        if preprocessed is None:
            return {"available": False, "error": "frame_decode_failed"}

        bgr_frame, rgb_frame = preprocessed

        gesture_result, pose_result, face_result = await asyncio.gather(
            asyncio.to_thread(session.gesture_detector.detect, frame_bytes),
            asyncio.to_thread(session.pose_detector.detect, rgb_frame),
            asyncio.to_thread(session.face_detector.detect, rgb_frame),
        )

        emotion_result = _emotion_detector.detect(face_result)

        curr_landmarks = pose_result.get("landmarks_xy") if pose_result.get("detected") else None
        movement_result = _movement_detector.detect(session.last_pose_landmarks, curr_landmarks)
        if curr_landmarks:
            session.last_pose_landmarks = curr_landmarks

        pain_result = _pain_detector.detect(emotion_result, pose_result, movement_result, annotation_point)

        session.frame_count += 1
        session.touch()

        observation = MultimodalFusion.fuse(
            consultation_id=session.consultation_id,
            gesture=gesture_result, pose=pose_result, face=face_result,
            emotion=emotion_result, movement=movement_result, pain=pain_result,
        )
        observation["frame_count"] = session.frame_count
        return observation
