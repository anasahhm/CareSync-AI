"""
GestureMed AI — Gesture Recognition Engine
Refactored from the original MediaPipe/OpenCV code into a clean,
testable, stateless service layer.

Usage:
    engine = GestureEngine()
    result = engine.process_frame(frame_bytes)
"""
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class HandLandmarkResult:
    gesture: str
    confidence: float
    finger_count: int
    fingers: list[int]
    hand_position: tuple[float, float]
    metadata: dict = field(default_factory=dict)


@dataclass
class GestureFrameResult:
    hands_detected: int
    primary_gesture: str
    confidence: float
    metadata: dict
    landmarks_raw: Optional[list] = None  # Serializable landmark data for WebSocket


# ── Core Gesture Logic (stateless) ────────────────────────────────────────────

class GestureRecognizer:
    """Pure gesture classification from MediaPipe landmarks. Stateless."""

    def count_extended_fingers(self, lm) -> tuple[int, list[int]]:
        fingers = []

        # Thumb
        thumb_tip = lm.landmark[4]
        thumb_ip  = lm.landmark[3]
        fingers.append(1 if abs(thumb_tip.x - thumb_ip.x) > 0.04 else 0)

        # Index, Middle, Ring, Pinky
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        for tip, pip in zip(tips, pips):
            fingers.append(1 if lm.landmark[tip].y < lm.landmark[pip].y - 0.02 else 0)

        return sum(fingers), fingers

    def detect_pinch(self, lm) -> bool:
        t = lm.landmark[4]
        i = lm.landmark[8]
        dist = math.sqrt((t.x - i.x) ** 2 + (t.y - i.y) ** 2)
        return dist < 0.05

    def detect_thumbs_up(self, lm) -> bool:
        thumb_up = lm.landmark[4].y < lm.landmark[2].y - 0.1
        count, _ = self.count_extended_fingers(lm)
        return thumb_up and count <= 2

    def detect_thumbs_down(self, lm) -> bool:
        thumb_down = lm.landmark[4].y > lm.landmark[2].y + 0.1
        count, _ = self.count_extended_fingers(lm)
        return thumb_down and count <= 2

    def detect_peace(self, lm) -> bool:
        count, fingers = self.count_extended_fingers(lm)
        return count == 2 and fingers[1] == 1 and fingers[2] == 1

    def detect_pointing(self, lm) -> bool:
        count, fingers = self.count_extended_fingers(lm)
        return count == 1 and fingers[1] == 1

    def detect_open_palm(self, lm) -> bool:
        count, _ = self.count_extended_fingers(lm)
        return count >= 4

    def detect_fist(self, lm) -> bool:
        count, _ = self.count_extended_fingers(lm)
        return count == 0

    def classify(self, lm) -> HandLandmarkResult:
        count, fingers = self.count_extended_fingers(lm)
        pos = (lm.landmark[0].x, lm.landmark[0].y)
        metadata: dict = {}

        if self.detect_pinch(lm):
            return HandLandmarkResult("PINCH", 0.95, count, fingers, pos, metadata)
        if self.detect_peace(lm):
            return HandLandmarkResult("PEACE", 0.90, count, fingers, pos, metadata)
        if self.detect_thumbs_up(lm):
            return HandLandmarkResult("THUMBS_UP", 0.90, count, fingers, pos, metadata)
        if self.detect_thumbs_down(lm):
            return HandLandmarkResult("THUMBS_DOWN", 0.90, count, fingers, pos, metadata)
        if self.detect_pointing(lm):
            idx_tip = lm.landmark[8]
            metadata["position"] = (idx_tip.x, idx_tip.y)
            return HandLandmarkResult("POINTING", 0.85, count, fingers, pos, metadata)
        if self.detect_open_palm(lm):
            return HandLandmarkResult("OPEN_PALM", 0.80, count, fingers, pos, metadata)
        if self.detect_fist(lm):
            return HandLandmarkResult("FIST", 0.80, count, fingers, pos, metadata)
        if 1 <= count <= 5:
            metadata["count"] = count
            return HandLandmarkResult(f"FINGERS_{count}", 0.75, count, fingers, pos, metadata)

        return HandLandmarkResult("NONE", 0.0, count, fingers, pos, metadata)


# ── Stateful Engine with Temporal Smoothing ────────────────────────────────────

class GestureEngine:
    """
    Stateful gesture engine. Wraps MediaPipe hand tracking
    and adds temporal smoothing + gesture hold detection.

    Thread-safety: each consultation session should have its own instance.
    """

    def __init__(self, max_num_hands: int = 2, min_confidence: float = 0.7):
        self._recognizer = GestureRecognizer()
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_confidence,
            min_tracking_confidence=min_confidence,
        )
        self._mp_draw = mp.solutions.drawing_utils

        # Temporal smoothing
        self._history: deque = deque(maxlen=5)
        self._current_gesture: str = "NONE"
        self._gesture_start: float = time.time()
        self._hold_duration: float = 0.0

    def process_frame(self, frame_bytes: bytes) -> GestureFrameResult:
        """
        Process a JPEG/PNG frame (as bytes) and return gesture result.
        Safe to call from an async handler via run_in_executor.
        """
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return GestureFrameResult(0, "NONE", 0.0, {})

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)

        if not results.multi_hand_landmarks:
            self._history.append("NONE")
            return GestureFrameResult(0, "NONE", 0.0, {})

        # Classify primary hand
        primary = results.multi_hand_landmarks[0]
        result = self._recognizer.classify(primary)

        # Temporal smoothing
        self._history.append(result.gesture)
        if len(self._history) >= 3:
            recent = list(self._history)
            smoothed = max(set(recent), key=recent.count)
        else:
            smoothed = result.gesture

        # Hold duration
        now = time.time()
        if smoothed == self._current_gesture:
            self._hold_duration = now - self._gesture_start
        else:
            self._current_gesture = smoothed
            self._gesture_start = now
            self._hold_duration = 0.0

        result.metadata["hold_duration"] = self._hold_duration
        result.metadata["hand_count"] = len(results.multi_hand_landmarks)

        # Serialize landmarks for WebSocket streaming
        landmarks_raw = []
        for hand_lm in results.multi_hand_landmarks:
            hand_data = [
                {"x": lm.x, "y": lm.y, "z": lm.z}
                for lm in hand_lm.landmark
            ]
            landmarks_raw.append(hand_data)

        return GestureFrameResult(
            hands_detected=len(results.multi_hand_landmarks),
            primary_gesture=smoothed,
            confidence=result.confidence,
            metadata=result.metadata,
            landmarks_raw=landmarks_raw,
        )

    def close(self):
        self._hands.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
