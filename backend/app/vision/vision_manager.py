"""
Vision Manager

Single async facade every agent, route, and the orchestrator uses to reach
the vision pipeline. Owns the CameraManager session registry, runs frames
through FramePipeline, publishes a VISION_OBSERVATION event on the shared
communication bus (so the live dashboard and consensus engine see it the
same way they see any agent event), and stores the latest observation in
MemoryManager's shared/consultation memory when one is configured.

If MediaPipe/OpenCV aren't installed at all, every detector reports
`available: False` and this manager still runs without raising - agents
that check `if self.vision` simply see empty observations and continue.
"""
import logging
from typing import Dict, Any, Optional

from app.vision.camera_manager import CameraManager
from app.vision.frame_pipeline import FramePipeline
from app.vision.speech_detector import SpeechDetector

logger = logging.getLogger(__name__)


class VisionManager:
    def __init__(self, communication_layer=None, memory_manager=None):
        self.camera_manager = CameraManager()
        self.communication = communication_layer
        self.memory_manager = memory_manager
        self._latest_observations: Dict[str, Dict[str, Any]] = {}
        self._speech_detector = SpeechDetector()

    def start_session(self, consultation_id: str) -> Dict[str, Any]:
        session = self.camera_manager.get_or_create(consultation_id)
        return {"consultation_id": consultation_id, "status": "started", "frame_count": session.frame_count}

    def stop_session(self, consultation_id: str) -> Dict[str, Any]:
        closed = self.camera_manager.close_session(consultation_id)
        self._latest_observations.pop(consultation_id, None)
        return {"consultation_id": consultation_id, "status": "stopped" if closed else "not_found"}

    async def process_frame(
        self, consultation_id: str, frame_bytes: bytes, annotation_point: Optional[tuple] = None
    ) -> Dict[str, Any]:
        session = self.camera_manager.get_or_create(consultation_id)
        observation = await FramePipeline.process(session, frame_bytes, annotation_point=annotation_point)

        if observation.get("available", True) is not False:
            self._latest_observations[consultation_id] = observation
            await self._publish_and_store(consultation_id, observation)

        return observation

    async def _publish_and_store(self, consultation_id: str, observation: Dict[str, Any]) -> None:
        if self.communication:
            try:
                from app.communication import create_agent_event, EventType
                event = create_agent_event(
                    event_type=EventType.VISION_OBSERVATION,
                    source_agent="VisionManager",
                    source_agent_id="vision-manager",
                    consultation_id=consultation_id,
                    payload={"observation": observation},
                )
                await self.communication.publish(event)
            except Exception as e:
                logger.warning(f"VisionManager: failed to publish observation event (non-fatal): {e}")

        if self.memory_manager:
            try:
                await self.memory_manager.shared_memory.write(
                    consultation_id, "latest_vision_observation", observation.get("summary")
                )
            except Exception as e:
                logger.warning(f"VisionManager: failed to store observation in memory (non-fatal): {e}")

    async def analyze_speech(self, consultation_id: str, audio_bytes: bytes) -> Dict[str, Any]:
        import asyncio
        speech_result = await asyncio.to_thread(self._speech_detector.detect, audio_bytes)

        existing = self._latest_observations.get(consultation_id)
        if existing:
            existing["modalities"]["speech"] = speech_result
            existing["summary"]["speech_emotion"] = speech_result.get("emotion") if speech_result.get("available") else None
            if speech_result.get("emotion") == "distressed_or_urgent":
                existing["summary"].setdefault("distress_flags", [])
                if "distressed_speech" not in existing["summary"]["distress_flags"]:
                    existing["summary"]["distress_flags"].append("distressed_speech")
            await self._publish_and_store(consultation_id, existing)

        return speech_result

    def get_latest_observation(self, consultation_id: str) -> Optional[Dict[str, Any]]:
        return self._latest_observations.get(consultation_id)

    def get_status(self, consultation_id: str) -> Dict[str, Any]:
        session = self.camera_manager.get(consultation_id)
        if not session:
            return {"consultation_id": consultation_id, "active": False}
        return {
            "consultation_id": consultation_id,
            "active": True,
            "frame_count": session.frame_count,
            "gesture_available": session.gesture_detector.available,
            "pose_available": session.pose_detector.available,
            "face_available": session.face_detector.available,
        }

    def cleanup_idle_sessions(self) -> int:
        return self.camera_manager.cleanup_idle_sessions()
