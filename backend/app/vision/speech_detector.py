"""
Speech (Emotion) Detector

Prosodic speech-emotion heuristic from a raw audio clip (WAV bytes):
pitch variability and energy/loudness variance. Uses librosa when
installed for real pitch tracking (free, local, MIT-licensed); falls back
to a stdlib-only RMS-energy-variance heuristic (via the `wave` and
`audioop`-free numpy path) when librosa/soundfile aren't installed, so
speech signal is still produced (lower fidelity) with zero extra installs.

This is intentionally NOT a full Whisper transcription pipeline - Whisper
is for speech-to-text, which is out of scope for "speech emotion"; if
transcription is later needed, WhisperTranscriber would live alongside
this file and feed text into the existing agent/RAG text path instead of
duplicating audio handling here.
"""
import io
import logging
import wave
from typing import Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    librosa = None
    LIBROSA_AVAILABLE = False

HIGH_ENERGY_VARIANCE_THRESHOLD = 0.02
HIGH_PITCH_VARIANCE_HZ = 40.0


class SpeechDetector:
    def __init__(self):
        self.available = True  # always at least the stdlib fallback path

    def detect(self, audio_bytes: bytes) -> Dict[str, Any]:
        try:
            if LIBROSA_AVAILABLE:
                return self._detect_with_librosa(audio_bytes)
            return self._detect_with_fallback(audio_bytes)
        except Exception as e:
            logger.warning(f"SpeechDetector: analysis failed ({e})")
            return {"available": False, "error": str(e)}

    def _detect_with_librosa(self, audio_bytes: bytes) -> Dict[str, Any]:
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
        if y.size == 0:
            return {"available": True, "detected": False}

        rms = librosa.feature.rms(y=y)[0]
        energy_variance = float(np.var(rms))

        f0, voiced_flag, _ = librosa.pyin(
            y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr
        )
        voiced = f0[~np.isnan(f0)] if f0 is not None else np.array([])
        pitch_variance = float(np.std(voiced)) if voiced.size > 0 else 0.0

        emotion, confidence = self._classify(energy_variance, pitch_variance)
        return {
            "available": True, "detected": True, "backend": "librosa",
            "energy_variance": round(energy_variance, 5),
            "pitch_variance_hz": round(pitch_variance, 2),
            "emotion": emotion, "confidence": confidence,
        }

    def _detect_with_fallback(self, audio_bytes: bytes) -> Dict[str, Any]:
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                sampwidth = wf.getsampwidth()
        except Exception:
            return {"available": True, "detected": False, "backend": "stdlib_fallback", "reason": "unsupported_audio_format"}

        dtype = np.int16 if sampwidth == 2 else np.uint8
        samples = np.frombuffer(frames, dtype=dtype).astype(np.float32)
        if samples.size == 0:
            return {"available": True, "detected": False, "backend": "stdlib_fallback"}

        chunk = max(1, samples.size // 20)
        rms_chunks = [
            float(np.sqrt(np.mean(np.square(samples[i:i + chunk])) + 1e-9))
            for i in range(0, samples.size, chunk)
        ]
        norm = max(rms_chunks) or 1.0
        rms_chunks = [r / norm for r in rms_chunks]
        energy_variance = float(np.var(rms_chunks))

        emotion, confidence = self._classify(energy_variance, pitch_variance_hz=0.0)
        return {
            "available": True, "detected": True, "backend": "stdlib_fallback",
            "energy_variance": round(energy_variance, 5),
            "emotion": emotion, "confidence": confidence,
        }

    def _classify(self, energy_variance: float, pitch_variance_hz: float) -> (str, float):
        if energy_variance > HIGH_ENERGY_VARIANCE_THRESHOLD or pitch_variance_hz > HIGH_PITCH_VARIANCE_HZ:
            return "distressed_or_urgent", 0.6
        if energy_variance < HIGH_ENERGY_VARIANCE_THRESHOLD * 0.2:
            return "flat_or_fatigued", 0.5
        return "calm", 0.5
