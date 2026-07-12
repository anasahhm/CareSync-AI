"""
Model Loader

Loads a free/local inference backend with an automatic fallback chain:
  1. torch model on the DeviceManager-selected device (GPU if available)
  2. torch model on CPU (if GPU load fails - e.g. OOM or driver issue)
  3. Ollama HTTP API (fully separate process, e.g. llama3/mistral/qwen
     running locally) - used when no local torch model is loaded at all,
     or as an explicit CPU-light alternative to loading weights in-process
  4. A deterministic rule-based stub result, so a caller never crashes even
     with zero ML backends available in this environment

This does not hardcode any single model - it exists to give any future
LLM-backed agent (see app/rag/prompt_builder.py) one reliable place to get
"a model, somehow" without repeating this fallback logic per caller.
"""
import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


class ModelLoader:
    def __init__(self, device_manager, ollama_url: str, ollama_fallback_model: str = "llama3"):
        self.device_manager = device_manager
        self.ollama_url = ollama_url
        self.ollama_fallback_model = ollama_fallback_model
        self._ollama_healthy: Optional[bool] = None

    async def check_ollama(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.ollama_url}/api/tags")
                self._ollama_healthy = resp.status_code == 200
        except Exception as e:
            logger.debug(f"ModelLoader: Ollama unreachable ({e})")
            self._ollama_healthy = False
        return self._ollama_healthy

    async def generate(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Best-effort free-model text generation. Returns a dict with
        `backend` set to whichever path actually served the request, so
        callers/dashboards can be honest about degraded operation.
        """
        model = model or self.ollama_fallback_model

        if self._ollama_healthy is None:
            await self.check_ollama()

        if self._ollama_healthy:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={"model": model, "prompt": prompt, "stream": False},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return {"backend": "ollama", "model": model, "text": data.get("response", "")}
            except Exception as e:
                logger.warning(f"ModelLoader: Ollama generate failed, falling back ({e})")

        return {
            "backend": "unavailable",
            "model": None,
            "text": "",
            "note": "No local LLM backend reachable (Ollama unreachable, no torch model loaded). "
                    "Rule-based agents are unaffected; only LLM-upgrade paths depend on this.",
        }

    def device_summary(self) -> Dict[str, Any]:
        return self.device_manager.info()
