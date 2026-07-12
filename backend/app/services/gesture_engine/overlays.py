"""
GestureMed AI — Gesture Overlays
OpenCV drawing utilities for annotation rendering.
Used server-side when generating annotated frame exports.
"""
import cv2
import numpy as np
from typing import List, Tuple


class AnnotationOverlay:
    """
    Renders annotation markers and gesture info onto OpenCV frames.
    Used for server-side recording annotation and report image generation.
    """

    # Color palette (BGR for OpenCV)
    COLORS = {
        "red": (80, 80, 255),
        "blue": (255, 120, 80),
        "green": (80, 220, 80),
        "yellow": (80, 220, 255),
        "purple": (200, 80, 200),
        "cyan": (220, 200, 80),
        "white": (255, 255, 255),
    }

    @staticmethod
    def draw_point_annotation(
        frame: np.ndarray,
        x_norm: float,
        y_norm: float,
        label: str = "",
        color: Tuple[int, int, int] = (80, 80, 255),
        radius: int = 20,
    ) -> np.ndarray:
        """Draw a circular annotation marker at normalized coordinates."""
        h, w = frame.shape[:2]
        px, py = int(x_norm * w), int(y_norm * h)

        overlay = frame.copy()
        cv2.circle(overlay, (px, py), radius, color, -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        cv2.circle(frame, (px, py), radius, color, 2)

        if label:
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(label, font, 0.5, 1)[0]
            cv2.rectangle(
                frame,
                (px + radius + 2, py - text_size[1] - 4),
                (px + radius + text_size[0] + 10, py + 4),
                (20, 20, 20),
                -1,
            )
            cv2.putText(frame, label, (px + radius + 6, py), font, 0.5, color, 1, cv2.LINE_AA)

        return frame

    @staticmethod
    def draw_landmark_skeleton(
        frame: np.ndarray,
        landmarks: List[dict],
        color: Tuple[int, int, int] = (100, 220, 255),
    ) -> np.ndarray:
        """Draw MediaPipe hand landmark skeleton from raw landmark dicts."""
        if not landmarks:
            return frame

        h, w = frame.shape[:2]
        points = [(int(lm["x"] * w), int(lm["y"] * h)) for lm in landmarks]

        # Connections matching MediaPipe HAND_CONNECTIONS
        connections = [
            (0,1),(1,2),(2,3),(3,4),       # thumb
            (0,5),(5,6),(6,7),(7,8),        # index
            (5,9),(9,10),(10,11),(11,12),   # middle
            (9,13),(13,14),(14,15),(15,16), # ring
            (13,17),(17,18),(18,19),(19,20),# pinky
            (0,17),
        ]

        for start, end in connections:
            if start < len(points) and end < len(points):
                cv2.line(frame, points[start], points[end], color, 1, cv2.LINE_AA)

        for point in points:
            cv2.circle(frame, point, 3, color, -1)

        return frame

    @staticmethod
    def draw_gesture_label(
        frame: np.ndarray,
        gesture: str,
        confidence: float,
        position: str = "top_right",
    ) -> np.ndarray:
        """Draw gesture name and confidence badge on frame."""
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"{gesture} ({int(confidence * 100)}%)"
        text_size = cv2.getTextSize(text, font, 0.6, 2)[0]

        if position == "top_right":
            x = w - text_size[0] - 20
            y = 40
        else:
            x, y = 20, 40

        cv2.rectangle(frame, (x - 10, y - 25), (x + text_size[0] + 10, y + 10), (20, 20, 20), -1)
        cv2.rectangle(frame, (x - 10, y - 25), (x + text_size[0] + 10, y + 10), (100, 220, 100), 2)
        cv2.putText(frame, text, (x, y), font, 0.6, (100, 220, 100), 2, cv2.LINE_AA)
        return frame

    @staticmethod
    def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
        """Convert CSS hex color to OpenCV BGR tuple."""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (b, g, r)

    @classmethod
    def render_annotations_on_frame(
        cls,
        frame: np.ndarray,
        annotations: List[dict],
    ) -> np.ndarray:
        """Render a list of annotation dicts onto a frame."""
        for ann in annotations:
            coords = ann.get("coordinates", {})
            x = coords.get("x", 0.5)
            y = coords.get("y", 0.5)
            hex_color = ann.get("color", "#FF6B6B")
            label = ann.get("body_region") or ann.get("note", "")
            color = cls.hex_to_bgr(hex_color)
            cls.draw_point_annotation(frame, x, y, label=label, color=color)
        return frame
