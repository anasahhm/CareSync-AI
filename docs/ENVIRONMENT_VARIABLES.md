# Environment Variables Reference

All variables are read via `pydantic-settings` in `backend/app/core/config.py`, with an optional `.env` file at the repo root (see `.env.example`). Frontend variables are read via Next.js's built-in `NEXT_PUBLIC_*` convention in `frontend/`.

## Application

| Variable | Used by | Required | Default | Example |
|---|---|---|---|---|
| `ENVIRONMENT` | `core/config.py` | No | `development` | `production` |
| `DEBUG` | `core/config.py` | No | `true` | `false` |
| `SECRET_KEY` | JWT signing (`core/security.py`) | **Yes, in production** | placeholder string | 64-char random string |

## Database

| Variable | Used by | Required | Default | Example |
|---|---|---|---|---|
| `DATABASE_URL` | `core/database.py` | Yes | local postgres URL | `postgresql+asyncpg://user:pass@postgres:5432/db` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Docker Compose only (feeds `DATABASE_URL`) | Yes (Docker) | `gesturemed` / `gesturemed` / `gesturemed_secret` | — |

## Redis

| Variable | Used by | Required | Default | Example |
|---|---|---|---|---|
| `REDIS_URL` | `memory/redis_cache.py`, RAG embedding cache | No — falls back to in-process dict | `redis://localhost:6379/0` | `redis://redis:6379/0` |

## AI Providers (paid, optional)

| Variable | Used by | Required | Default | Example |
|---|---|---|---|---|
| `AI_PROVIDER` | `services/ai/report_generator.py` | No | `anthropic` | `openai` |
| `AI_MODEL` | same | No | `claude-opus-4-20250514` | — |
| `ANTHROPIC_API_KEY` | same | No — falls back to free Ollama path, then stub | empty | `sk-ant-...` |
| `OPENAI_API_KEY` | same | No — same fallback | empty | `sk-...` |

## RAG (V2, free/local by default)

| Variable | Used by | Required | Default | Example |
|---|---|---|---|---|
| `QDRANT_URL` | `rag/vector_store.py` | No — falls back to in-memory FAISS | `http://localhost:6333` | `http://qdrant:6333` |
| `OLLAMA_URL` | `rag/embedding_service.py`, `gpu/model_loader.py` | No — falls back to hashed embeddings / stub | `http://localhost:11434` | `http://ollama:11434` |
| `RAG_ENABLE_PUBMED` | `rag/evidence_retriever.py` | No | `true` | `false` |
| `EMBEDDING_MODEL` | `rag/embedding_service.py` | No | `all-MiniLM-L6-v2` | any sentence-transformers model name |

## GPU / ROCm (V2)

| Variable | Used by | Required | Default | Example |
|---|---|---|---|---|
| `GPU_ENABLED` | `services/agent_service.py` (informational) | No | `true` | `false` |
| `GPU_BACKEND` | `gpu/device_manager.py` | No | `auto` | `rocm` / `cuda` / `cpu` |
| `GPU_MEMORY_FRACTION` | reserved for future memory-pooling use | No | `0.9` | `0.8` |
| `OLLAMA_FALLBACK_MODEL` | `gpu/model_loader.py`, report generation free path | No | `llama3` | `mistral` |

## JWT

| Variable | Used by | Required | Default | Example |
|---|---|---|---|---|
| `ALGORITHM` | `core/security.py` | No | `HS256` | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | same | No | `30` | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | same | No | `7` | `14` |

## CORS / Uploads

| Variable | Used by | Required | Default | Example |
|---|---|---|---|---|
| `CORS_ORIGINS` | `main.py` | No | `http://localhost:3000,http://localhost:3001` | comma-separated origin list |
| `UPLOAD_DIR` | `main.py` | No | `uploads` | `/data/uploads` |
| `MAX_UPLOAD_SIZE` | upload validation | No | `52428800` (50MB) | bytes |

## Frontend (Next.js)

| Variable | Used by | Required | Default | Example |
|---|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | `frontend/src/lib/api.ts` | Yes | `http://localhost:8000` | `https://api.yourdomain.com` |
| `NEXT_PUBLIC_WS_URL` | `frontend/src/hooks/useConsultationSocket.ts` | Yes | `ws://localhost:8000` | `wss://api.yourdomain.com` |

## Legacy / not currently wired (documented for transparency)

| Variable | Status |
|---|---|
| `BAND_ENABLED`, `BAND_API_KEY`, `BAND_ORG_ID`, `BAND_FALLBACK_MODE` | Defined in `config.py` but **not read by any active code path** — `app/communication/band_event_bus.py` implements a Redis-pub/sub "Band SDK simulation" but is never instantiated by `agent_registry.py` (which uses `LocalEventBus`/`AgentCommunicationLayer` directly). See the audit report. Setting these has no effect currently. |
| `DEMO_MODE`, `DEMO_PATIENT_NAME`, `DEMO_CHIEF_COMPLAINT`, `DEMO_PAIN_SCORE`, `DEMO_MEDICAL_HISTORY`, `DEMO_INSURANCE_PLAN` | Used by `api/routes/demo.py` for the one-click judge demo seed data. |
| `AGENT_TIMEOUT_SECONDS`, `AGENT_MAX_RETRIES` | Defined in config but each agent currently sets its own `TIMEOUT_SECONDS` class attribute independently rather than reading these globals — effectively unused. |
