"""
Device Manager

Detects available compute backends in priority order: AMD ROCm -> NVIDIA
CUDA -> CPU, and exposes a single `get_device()` any AI-facing service can
call without knowing or caring what hardware is actually present. Torch is
imported lazily and optionally - if it isn't installed at all (true in this
sandbox, and true for a pure-CPU hackathon deployment), every method still
returns a valid, honest CPU-backed result instead of raising.

ROCm note: PyTorch's ROCm build reports itself through the same
`torch.cuda` API surface as NVIDIA CUDA (`torch.version.hip` is set instead
of `torch.version.cuda` on ROCm builds) - there is no separate `torch.rocm`
namespace, so detection here checks `torch.version.hip` to distinguish them.
"""
import logging

from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

class DeviceManager:
    def __init__(self, preferred_backend: str = "auto"):
        self.preferred_backend = preferred_backend
        self._device_info: Optional[Dict[str, Any]] = None
        self._detect()

    def _detect(self) -> None:
        info = {
            "torch_available": TORCH_AVAILABLE,
            "backend": "cpu",
            "device_str": "cpu",
            "device_name": "CPU",
            "is_rocm": False,
            "is_cuda": False,
            "device_count": 0,
        }

        if TORCH_AVAILABLE and self.preferred_backend != "cpu":
            try:
                if torch.cuda.is_available():
                    is_rocm = bool(getattr(torch.version, "hip", None))
                    if self.preferred_backend in ("auto", "rocm" if is_rocm else "cuda", "cuda"):
                        info["backend"] = "rocm" if is_rocm else "cuda"
                        info["device_str"] = "cuda:0"  # ROCm builds also expose the cuda:N API
                        info["is_rocm"] = is_rocm
                        info["is_cuda"] = not is_rocm
                        info["device_count"] = torch.cuda.device_count()
                        try:
                            info["device_name"] = torch.cuda.get_device_name(0)
                        except Exception:
                            info["device_name"] = "GPU (name unavailable)"
            except Exception as e:
                logger.warning(f"DeviceManager: GPU detection failed, falling back to CPU ({e})")

        self._device_info = info
        logger.info(f"DeviceManager: selected backend={info['backend']} device={info['device_str']}")

    @property
    def backend(self) -> str:
        return self._device_info["backend"]

    @property
    def device_str(self) -> str:
        return self._device_info["device_str"]

    def get_device(self):
        """Returns a torch.device if torch is installed, else the string 'cpu'."""
        if TORCH_AVAILABLE:
            return torch.device(self._device_info["device_str"])
        return "cpu"

    def info(self) -> Dict[str, Any]:
        return dict(self._device_info)

    def refresh(self) -> Dict[str, Any]:
        self._detect()
        return self.info()
