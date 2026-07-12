# Deployment Guide

No Kubernetes, no Helm, no Terraform anywhere in this project — **Docker Compose only**, by explicit project requirement.

## Option A — `docker-compose.yml` (original V1 stack)

Postgres, Redis, backend, frontend, nginx. No Qdrant/Ollama/GPU services — the V2 code detects their absence and runs on FAISS/CPU/heuristic fallbacks automatically.

```bash
cp .env.example .env
docker compose up -d
```

## Option B — `docker-compose.amd.yml` (full V2 stack, AMD/ROCm)

Adds Qdrant, Ollama, Prometheus, Grafana, and builds the backend + celery worker from `backend/Dockerfile.amd` (based on `rocm/pytorch`) with `/dev/kfd` and `/dev/dri` GPU passthrough.

```bash
cp .env.example .env
docker compose -f docker-compose.amd.yml up -d
```

Services and ports:

| Service | Port | Notes |
|---|---|---|
| nginx | 80, 443 | reverse proxy |
| frontend | 3000 | Next.js |
| backend | 8000 | FastAPI, ROCm image |
| postgres | 5432 | |
| redis | 6379 | |
| qdrant | 6333, 6334 | |
| ollama | 11434 | pull a model after first boot: `docker exec -it <ollama-container> ollama pull llama3` |
| prometheus | 9090 | scrapes `backend:8000/metrics` every 15s |
| grafana | 3001 | default login `admin`/`admin` unless overridden by `GRAFANA_ADMIN_USER`/`GRAFANA_ADMIN_PASSWORD` |

Startup ordering: `backend` has `depends_on` with `condition: service_healthy` for postgres/redis/qdrant/ollama, so it waits for each to pass its healthcheck before starting. `celery_worker`, `frontend`, `nginx`, `prometheus`, `grafana` depend on `backend`/`prometheus` respectively but not with health-gating (acceptable — each degrades gracefully if its dependency is briefly unavailable, per the fallback design documented in `SYSTEM_DESIGN.md`).

## AMD Developer Cloud specifics

1. Provision an AMD Developer Cloud instance with ROCm drivers pre-installed (verify with `rocm-smi` on the host before starting containers).
2. Clone the repo, `cp .env.example .env`, fill in `SECRET_KEY` at minimum.
3. `docker compose -f docker-compose.amd.yml up -d`.
4. Verify GPU passthrough: `docker exec -it <backend-container> python3 -c "from app.gpu import GPUManager; import asyncio; print(asyncio.run(GPUManager(backend='auto', ollama_url='http://ollama:11434').initialize()))"` — expect `"backend": "rocm"` if the GPU is visible; `"cpu"` is also a valid, working result (fallback), not a failure.
5. Expose port 80/443 in the instance's security group/firewall; point DNS at the instance if using a domain.

`HSA_OVERRIDE_GFX_VERSION=10.3.0` is set in `Dockerfile.amd` as a common compatibility default for consumer/prosumer AMD GPUs not on ROCm's official support matrix — adjust or remove per your specific card's ROCm compatibility (check `rocminfo` on the host).

## What is NOT independently verified in this sandbox

This development sandbox has no Docker daemon and no AMD GPU, so the following are **written and reviewed, but not executed here**:
- `docker compose build` / `up` actually succeeding end-to-end
- ROCm device passthrough actually detecting a GPU inside the container
- Prometheus actually scraping a running backend
- Grafana actually rendering a dashboard against live data

Everything else in this repo (backend Python execution, all fallback chains, frontend build/lint/typecheck) **was** actually executed and verified — see `RUNBOOK.md` and the audit report for the itemized list.
