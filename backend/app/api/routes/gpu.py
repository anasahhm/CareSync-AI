"""CareSyncAI V2 — GPU / ROCm Status API"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.models import User
from app.services.agent_service import get_agent_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def gpu_status(current_user: User = Depends(get_current_user)):
    agent_service = await get_agent_service()
    if not agent_service.gpu_manager:
        raise HTTPException(status_code=503, detail="GPU system not initialized")
    return await agent_service.gpu_manager.status()


@router.get("/health")
async def gpu_health(current_user: User = Depends(get_current_user)):
    agent_service = await get_agent_service()
    if not agent_service.gpu_manager:
        raise HTTPException(status_code=503, detail="GPU system not initialized")
    return await agent_service.gpu_manager.health.check()


@router.get("/benchmark")
async def gpu_benchmark(current_user: User = Depends(get_current_user)):
    agent_service = await get_agent_service()
    if not agent_service.gpu_manager:
        raise HTTPException(status_code=503, detail="GPU system not initialized")

    import time
    device_manager = agent_service.gpu_manager.device_manager
    info = device_manager.info()

    try:
        import torch
        device = device_manager.get_device()
        sizes = [256, 512, 1024]
        results = []
        for size in sizes:
            x = torch.rand(size, size, device=device)
            start = time.perf_counter()
            for _ in range(5):
                _ = x @ x
            if info["is_cuda"] or info["is_rocm"]:
                torch.cuda.synchronize()
            elapsed = (time.perf_counter() - start) / 5
            results.append({"matrix_size": size, "avg_matmul_seconds": round(elapsed, 6)})
        return {"device": info, "benchmark": results}
    except ImportError:
        return {"device": info, "benchmark": [], "note": "torch not installed; benchmark unavailable"}
