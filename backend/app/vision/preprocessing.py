"""
Preprocessing

Frame decode/normalize utilities shared by every detector, plus a light
medical-image preprocessing step (contrast/illumination normalization) so
downstream MediaPipe/YOLO models get a more consistent input regardless of
webcam exposure. Pure OpenCV/NumPy - no extra dependencies.
"""
import logging
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

MAX_DIMENSION = 960  # cap resolution for CPU-friendly inference


def decode_frame(frame_bytes: bytes) -> Optional[np.ndarray]:
    """Decode JPEG/PNG bytes (as sent from the browser) into a BGR ndarray."""
    try:
        arr = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        logger.warning(f"preprocessing: failed to decode frame ({e})")
        return None


def resize_for_inference(frame: np.ndarray, max_dim: int = MAX_DIMENSION) -> np.ndarray:
    h, w = frame.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale < 1.0:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return frame


def normalize_illumination(frame: np.ndarray) -> np.ndarray:
    """CLAHE-based contrast normalization on the luminance channel only,
    to reduce false negatives from poor webcam lighting without distorting color-based signals."""
    try:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        merged = cv2.merge((l, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    except Exception as e:
        logger.debug(f"preprocessing: illumination normalization skipped ({e})")
        return frame


def to_rgb(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def preprocess(frame_bytes: bytes) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """
    Full pipeline: decode -> resize -> normalize -> RGB conversion.
    Returns (bgr_frame, rgb_frame) or None if decoding failed.
    """
    frame = decode_frame(frame_bytes)
    if frame is None:
        return None
    frame = resize_for_inference(frame)
    frame = normalize_illumination(frame)
    rgb = to_rgb(frame)
    return frame, rgb
