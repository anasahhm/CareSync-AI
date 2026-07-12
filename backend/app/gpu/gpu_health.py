"""
GPU Health

Lightweight health check: can we place a tensor on the selected device and
run one op? Distinguishes "no GPU present" (healthy - CPU mode is a valid,
expected state) from "GPU present but broken" (unhealthy - e.g. ROCm driver
mismatch), which matters for a Docker healthcheck that shouldn't fail just
because a box has no GPU.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


class GPUHealth:
    def __init__(self, device_manager):
        self.device_manager = device_manager

    async def check(self) -> Dict[str, Any]:
        info = self.device_manager.info()

        if info["backend"] == "cpu":
            return {"healthy": True, "backend": "cpu", "reason": "No GPU requested/available; CPU mode is expected and healthy"}

        if not TORCH_AVAILABLE:
            return {"healthy": False, "backend": info["backend"], "reason": "GPU backend selected but torch is not installed"}

        try:
            device = self.device_manager.get_device()
            x = torch.rand(4, 4, device=device)
            y = x @ x
            _ = y.sum().item()
            return {"healthy": True, "backend": info["backend"], "reason": "Test tensor op succeeded on GPU"}
        except Exception as e:
            logger.error(f"GPUHealth: GPU test op failed ({e})")
            return {"healthy": False, "backend": info["backend"], "reason": f"GPU test op failed: {e}"}
