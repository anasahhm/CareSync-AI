# CareSyncAI

> **A 17-agent, real-time collaborative medical AI platform** : vision-aware, memory-aware, RAG-backed, and GPU/ROCm-accelerated, built on top of the original GestureMed AI gesture-controlled telemedicine platform.

**Stack:** FastAPI · Next.js 15 · Socket.IO · PostgreSQL · Redis · Qdrant (+ FAISS fallback) · Ollama (+ sentence-transformers) · MediaPipe/OpenCV · PyTorch (ROCm/CUDA/CPU) · Docker Compose

---

## What this is

CareSyncAI V2 is a full-stack, AI-native telemedicine platform that combines gesture-controlled WebRTC video consultations, Claude-generated medical reports, and a real-time multi-agent clinical decision-support system into a unified healthcare platform:

- **17 agents** run in a dependency-ordered, real-time collaborative pipeline (not sequential) — including Clinical Review, Medical History, Compliance & Privacy, Triage Escalation, Treatment Recommendation, Insurance Verification, Follow-up Coordination, Chief Orchestrator, Symptom Analysis, Diagnostic Reasoning, Medical Research, Evidence Retrieval, Hallucination Detection, Quality Assurance, Consensus Moderator, Explanation, and Escalation.
- **Real consensus**, not a vote count: weighted confidence scoring, moderator tie-breaking, and a dedicated safety-net escalation agent that aggregates every risk signal raised during the run.
- **Vision pipeline**: MediaPipe-based gesture, pose, and face detection, heuristic emotion/pain/movement analysis, and optional speech-emotion analysis, fused into a structured observation that becomes a weighted participant in consensus , not just a UI overlay.
- **RAG**: Hybrid dense retrieval (sentence-transformers → Qdrant/FAISS) combined with BM25 over a curated clinical guideline corpus, plus live PubMed lookup, with citation tracking and a grounding validator
- **Memory**: Short-term (per consultation), shared (cross-agent), and long-term (per patient, semantic-search-backed) memory, Redis-backed with automatic in-process fallback.
- **GPU/ROCm**: Automatic AMD ROCm → NVIDIA CUDA → CPU device detection, with an Ollama-backed free-model fallback chain for future LLM upgrades. The platform is fully functional on the free tier by default, requiring no paid API key for the multi-agent pipeline.

Every component degrades gracefully: no Qdrant → FAISS in-memory; no GPU → CPU; no Ollama → deterministic heuristics; no sentence-transformers → hashed bag-of-words embeddings. The platform is designed to run correctly on a standard laptop with only the base Python and Node.js toolchain installed, while progressively improving as optional services become available.

---

## Repository layout

```
med/
├── backend/                 FastAPI app
│   ├── app/
│   │   ├── agents/          17 agent implementations
│   │   ├── orchestration/    ConsultationOrchestrator, ConsensusEngine, WorkflowCoordinator, EventStore, ReportAggregator
│   │   ├── communication/   Event bus (local + Redis-capable), event types
│   │   ├── memory/          RedisCache, ConsultationMemory, PatientMemory, SemanticMemory, SharedMemory
│   │   ├── rag/              EmbeddingService, VectorStore, BM25Index, RetrievalEngine, GuidelineRetriever, PubMedRetriever, EvidenceRetriever, CitationEngine
│   │   ├── vision/           Preprocessing, gesture/pose/face/emotion/movement/pain/speech detectors, fusion, VisionManager
│   │   ├── gpu/              DeviceManager, GPUMetrics, GPUHealth, InferenceScheduler, ModelLoader
│   │   ├── api/routes/       REST endpoints (auth, consultations, video, gpu, memory, rag, reports, metrics, ...)
│   │   ├── services/         AgentService (lifecycle), gesture_engine (original hand-tracking), ai/ (report generation)
│   │   └── models/           SQLAlchemy models
│   ├── Dockerfile            CPU image
│   ├── Dockerfile.amd        ROCm image
│   ├── requirements.txt      Base deps (no torch)
│   └── requirements-gpu.txt  Optional torch (ROCm/CUDA install instructions inline)
├── frontend/                 Next.js 15 App Router
│   └── src/
│       ├── components/       dashboard/, consultation/, agents/, vision (VisionPanel), gpu (GPUDashboard), memory/, rag/, common/ (ErrorBoundary, Skeleton)
│       ├── providers/        NotificationProvider
│       ├── hooks/             useConsultationSocket, useGestureCamera, ...
│       └── lib/api.ts        Typed API client
├── docker-compose.yml         V1 stack (Postgres, Redis, backend, frontend, nginx)
├── docker-compose.amd.yml    Full V2 stack (+ Qdrant, Ollama, Prometheus, Grafana, GPU passthrough)
├── docker/                    prometheus.yml, grafana provisioning, nginx.conf
└── docs/                      This documentation set
```

---

## Quick start (local, no Docker, CPU-only, free-tier)

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # edit as needed - nothing is required to boot
uvicorn app.main:app --reload

# in another terminal
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Everything works with zero external services: Redis/Qdrant/Ollama absence is detected automatically and the app falls back to in-process/FAISS/CPU equivalents (see `docs/ARCHITECTURE.md` for the fallback chain diagram).

## Quick start (full stack, Docker Compose, AMD/ROCm)

```bash
cp .env.example .env   # add ANTHROPIC_API_KEY/OPENAI_API_KEY if you want paid-tier reports too
docker compose -f docker-compose.amd.yml up -d
```


## Documentation index

| Doc | Contents |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System diagrams (Mermaid) for every major subsystem |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Every REST endpoint: method, request, response, auth ||
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | Install/run/verify instructions for every subsystem |

## License / disclaimer

This is a hackathon prototype. It is **not** a certified medical device and does not provide medical diagnoses. Every AI-generated recommendation carries an explicit disclaimer and a "requires doctor review" flag when risk or hallucination signals are high .
