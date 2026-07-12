"""
GPU Metrics

Reads live utilization/memory stats. Tries `rocm-smi` (AMD) then `nvidia-smi`
(NVIDIA) as subprocesses (both are plain CLI tools, no Python bindings
required), falling back to torch.cuda memory stats, then to an honest
"no GPU" payload. Never raises - a missing tool just means fewer fields.
"""
import asyncio
import logging
import shutil
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


class GPUMetrics:
    def __init__(self, device_manager):
        self.device_manager = device_manager

    async def collect(self) -> Dict[str, Any]:
        info = self.device_manager.info()

        if info["is_rocm"] and shutil.which("rocm-smi"):
            metrics = await self._read_rocm_smi()
            if metrics:
                return {**info, **metrics, "source": "rocm-smi"}

        if info["is_cuda"] and shutil.which("nvidia-smi"):
            metrics = await self._read_nvidia_smi()
            if metrics:
                return {**info, **metrics, "source": "nvidia-smi"}

        if TORCH_AVAILABLE and (info["is_cuda"] or info["is_rocm"]):
            try:
                allocated = torch.cuda.memory_allocated(0)
                reserved = torch.cuda.memory_reserved(0)
                return {
                    **info,
                    "memory_allocated_mb": round(allocated / (1024 ** 2), 1),
                    "memory_reserved_mb": round(reserved / (1024 ** 2), 1),
                    "source": "torch.cuda",
                }
            except Exception as e:
                logger.debug(f"GPUMetrics: torch memory stats unavailable ({e})")

        return {**info, "source": "none", "note": "No GPU monitoring tool available; running CPU-only"}

    async def _read_rocm_smi(self) -> Optional[Dict[str, Any]]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "rocm-smi", "--showuse", "--showmeminfo", "vram", "--json",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            import json
            data = json.loads(stdout.decode() or "{}")
            return {"raw": data}
        except Exception as e:
            logger.debug(f"GPUMetrics: rocm-smi read failed ({e})")
            return None

    async def _read_nvidia_smi(self) -> Optional[Dict[str, Any]]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            line = stdout.decode().strip().split("\n")[0]
            util, mem_used, mem_total = [x.strip() for x in line.split(",")]
            return {
                "gpu_utilization_pct": float(util),
                "memory_used_mb": float(mem_used),
                "memory_total_mb": float(mem_total),
            }
        except Exception as e:
            logger.debug(f"GPUMetrics: nvidia-smi read failed ({e})")
            return None
