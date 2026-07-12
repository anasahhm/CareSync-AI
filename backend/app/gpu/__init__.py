"""
GPU / ROCm Layer

Exports DeviceManager (ROCm/CUDA/CPU auto-detection), GPUMetrics,
GPUHealth, InferenceScheduler (async batching queue), ModelLoader
(GPU -> CPU -> Ollama -> stub fallback chain), and GPUManager (the facade
the rest of the app wires into).
"""
import logging
from typing import Dict, Any

from app.gpu.device_manager import DeviceManager
from app.gpu.gpu_metrics import GPUMetrics
from app.gpu.gpu_health import GPUHealth
from app.gpu.inference_scheduler import InferenceScheduler
from app.gpu.model_loader import ModelLoader

logger = logging.getLogger(__name__)


class GPUManager:
    def __init__(self, backend: str = "auto", ollama_url: str = "http://localhost:11434", ollama_fallback_model: str = "llama3"):
        self.device_manager = DeviceManager(preferred_backend=backend)
        self.metrics = GPUMetrics(self.device_manager)
        self.health = GPUHealth(self.device_manager)
        self.model_loader = ModelLoader(self.device_manager, ollama_url, ollama_fallback_model)

    async def initialize(self) -> Dict[str, Any]:
        await self.model_loader.check_ollama()
        info = self.device_manager.info()
        logger.info(f"GPUManager initialized: {info}")
        return info

    async def status(self) -> Dict[str, Any]:
        metrics = await self.metrics.collect()
        health = await self.health.check()
        return {"device": self.device_manager.info(), "metrics": metrics, "health": health}


__all__ = ["DeviceManager", "GPUMetrics", "GPUHealth", "InferenceScheduler", "ModelLoader", "GPUManager"]
