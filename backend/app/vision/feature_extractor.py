"""
Feature Extractor

Shared geometry helpers for turning MediaPipe landmark sets into simple
numeric features (distances, angles, ratios) that the heuristic detectors
(emotion, pain, movement) build on. Kept detector-agnostic so pose/face
detectors don't each reimplement vector math.
"""
import math
from typing import List, Tuple


def euclidean(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def midpoint(p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[float, float]:
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


def angle_between(p1: Tuple[float, float], vertex: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Angle at `vertex` formed by p1-vertex-p2, in degrees."""
    v1 = (p1[0] - vertex[0], p1[1] - vertex[1])
    v2 = (p2[0] - vertex[0], p2[1] - vertex[1])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag1 = math.hypot(*v1)
    mag2 = math.hypot(*v2)
    if mag1 == 0 or mag2 == 0:
        return 0.0
    cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cos_angle))


def landmark_to_xy(landmark) -> Tuple[float, float]:
    return (landmark.x, landmark.y)


def landmark_displacement(prev: List[Tuple[float, float]], curr: List[Tuple[float, float]]) -> float:
    """Average per-point displacement between two landmark frames - a cheap
    proxy for movement magnitude without full optical flow."""
    if not prev or not curr or len(prev) != len(curr):
        return 0.0
    total = sum(euclidean(p, c) for p, c in zip(prev, curr))
    return total / len(prev)
