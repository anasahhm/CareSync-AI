# CareSyncAI

> **A 17-agent, real-time collaborative medical AI platform** — vision-aware, memory-aware, RAG-backed, and GPU/ROCm-accelerated, built on top of the original GestureMed AI gesture-controlled telemedicine platform.

**Stack:** FastAPI · Next.js 15 · Socket.IO · PostgreSQL · Redis · Qdrant (+ FAISS fallback) · Ollama (+ sentence-transformers) · MediaPipe/OpenCV · PyTorch (ROCm/CUDA/CPU) · Docker Compose

---

## What this is

CareSyncAI V2 evolves the original GestureMed AI product (gesture-controlled, WebRTC video telemedicine with Claude-generated reports) into a full multi-agent clinical decision-support system, while keeping every original feature working:

- **17 agents** run in a dependency-ordered, real-time collaborative pipeline (not sequential) — the original 7 (Clinical Review, Medical History, Compliance & Privacy, Triage Escalation, Treatment Recommendation, Insurance Verification, Followup Coordination) plus 10 added in V2 (Chief Orchestrator, Symptom, Diagnostic, Medical Research, Evidence, Hallucination Detection, Quality Assurance, Consensus Moderator, Explanation, Escalation).
- **Real consensus**, not a vote count: weighted confidence scoring, moderator tie-breaking, and a dedicated safety-net escalation agent that aggregates every risk signal raised during the run.
- **Vision pipeline**: MediaPipe-based gesture/pose/face detection, heuristic emotion/pain/movement analysis, and optional speech-emotion analysis, fused into one structured observation that becomes a weighted participant in consensus — not just a UI overlay.
- **RAG**: hybrid dense (sentence-transformers → Qdrant/FAISS) + BM25 retrieval over a curated clinical guideline corpus, plus live PubMed lookup, with citation tracking and a grounding validator.
- **Memory**: short-term (per-consultation), shared (cross-agent), and long-term (per-patient, semantic-search-backed) memory, Redis-backed with automatic in-process fallback.
- **GPU/ROCm**: automatic AMD ROCm → NVIDIA CUDA → CPU device detection, with an Ollama-backed free-model fallback chain for any LLM-upgrade path — the system is fully functional and free-tier-only by default (no paid API key required for the multi-agent pipeline itself).

Every one of the above degrades gracefully: no Qdrant → FAISS in-memory; no GPU → CPU; no Ollama → deterministic heuristic; no sentence-transformers → hashed bag-of-words embeddings. The system is designed to run correctly on a laptop with nothing installed beyond the base Python/Node toolchain, and to get measurably better as you add each optional service.

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

See `docs/DEPLOYMENT.md` for the full breakdown, health-check ordering, and AMD Developer Cloud specifics, and `docs/RUNBOOK.md` for step-by-step verification of every subsystem.

## Documentation index

| Doc | Contents |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System diagrams (Mermaid) for every major subsystem |
| [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md) | Design decisions, tradeoffs, limitations, future work |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Docker Compose, AMD Developer Cloud, ROCm setup |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Every REST endpoint: method, request, response, auth |
| [`docs/ENVIRONMENT_VARIABLES.md`](docs/ENVIRONMENT_VARIABLES.md) | Full env var table: used-by, required, default |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | Install/run/verify instructions for every subsystem |
| [`docs/HACKATHON_PRESENTATION.md`](docs/HACKATHON_PRESENTATION.md) | 2/5/10-minute demo scripts |
| [`docs/JUDGE_QA.md`](docs/JUDGE_QA.md) | Anticipated judge questions with direct answers |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | Literal click-by-click demo walkthrough |

## License / disclaimer

This is a hackathon prototype. It is **not** a certified medical device and does not provide medical diagnoses. Every AI-generated recommendation carries an explicit disclaimer and a "requires doctor review" flag when risk or hallucination signals are high — see `docs/SYSTEM_DESIGN.md` for the safety architecture.
