"""
Vision & Multimodal Intelligence Layer

camera -> preprocessing -> parallel detectors (gesture/pose/face/emotion/
movement/pain/speech) -> fusion -> structured medical observations ->
agent events. Every detector degrades gracefully (available: False) if its
underlying model/library isn't installed, so the pipeline never crashes
the consultation - see individual detector modules for fallback behavior.

Exports VisionManager, the single async entry point used everywhere else.
"""
from app.vision.vision_manager import VisionManager

__all__ = ["VisionManager"]
