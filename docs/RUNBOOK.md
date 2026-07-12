# Runbook

Step-by-step install, run, and verification instructions for every subsystem, from zero external services up to the full stack.

## Prerequisites

- Python 3.11+ (backend)
- Node.js 20+ (frontend)
- Optional: Docker + Docker Compose, Redis, PostgreSQL, Qdrant, Ollama, an AMD/NVIDIA GPU

## 1. Backend — bare minimum (CPU, no external services)

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn app.main:app --reload
```

Verify it booted: `curl http://localhost:8000/docs` should return the Swagger UI HTML. Check the startup log for lines like `RedisCache: could not connect... using in-process fallback` and `VectorStore: Qdrant unreachable... using in-memory FAISS fallback` — **these are expected**, not errors, when running without Docker.

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Register a doctor and a patient account, start a consultation, and confirm the video call UI loads.

## 3. Verify the multi-agent pipeline

```bash
curl -X POST http://localhost:8000/api/agents/process/<consultation_id> \
  -H "Authorization: Bearer <access_token>"
```

Expect a JSON response with `consensus.primary_diagnosis`, `consensus.consensus_score`, and `consensus.overall_risk_score`. Then:

```bash
curl http://localhost:8000/api/agents/timeline/<consultation_id> -H "Authorization: Bearer <token>"
```

Expect `event_count` > 0 and a list of `agent_started`/`agent_completed`/... events.

## 4. Verify Vision

Start a video session, POST a frame:

```bash
curl -X POST http://localhost:8000/api/video/start -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" -d '{"consultation_id": "<id>"}'

curl -X POST http://localhost:8000/api/video/frame -H "Authorization: Bearer <token>" \
  -F "consultation_id=<id>" -F "frame=@test.jpg"
```

Expect a `summary` object with `pain_score`, `emotion`, `posture`, etc. If MediaPipe's legacy `solutions` API isn't available in your installed `mediapipe` version, detector fields report `"available": false` rather than erroring — verify with:

```bash
python3 -c "import mediapipe as mp; print(hasattr(mp, 'solutions'))"
```

If `False`, pin `mediapipe==0.10.14` (the version in `requirements.txt`) rather than a newer release.

## 5. Verify RAG

```bash
curl -X POST http://localhost:8000/api/rag/search -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" -d '{"query": "acute coronary syndrome chest pain", "top_k": 3}'
```

Expect `guideline_hits` with `hybrid_score` fields and non-empty `citations`. Then:

```bash
curl http://localhost:8000/api/rag/health -H "Authorization: Bearer <token>"
```

Expect `"backend": "faiss_fallback"` (no Qdrant) or `"backend": "qdrant"` (Docker stack).

## 6. Verify Memory

```bash
curl http://localhost:8000/api/memory/consultation/<consultation_id> -H "Authorization: Bearer <token>"
curl http://localhost:8000/api/memory/health -H "Authorization: Bearer <token>"
```

Expect `redis_connected: false` and correct in-process data if Redis isn't running; `true` if it is.

## 7. Verify GPU layer

```bash
curl http://localhost:8000/api/gpu/status -H "Authorization: Bearer <token>"
```

Expect `"backend": "cpu"` on a machine with no GPU/torch installed — this is a healthy, correct result, not a failure. On an AMD box with `torch` (ROCm build) installed, expect `"backend": "rocm"`.

## 8. Verify Reports (PDF/Markdown/JSON export)

```bash
curl -X POST http://localhost:8000/api/reports/<consultation_id>/generate -H "Authorization: Bearer <token>"
# wait a few seconds for async generation
curl http://localhost:8000/api/reports/<consultation_id>/export/pdf -H "Authorization: Bearer <token>" -o report.pdf
file report.pdf   # should say "PDF document"
```

## 9. Verify metrics

```bash
curl http://localhost:8000/metrics
```

Expect Prometheus text format (`# HELP`, `# TYPE` lines) with no authentication required.

## 10. Frontend static verification (no server needed)

```bash
cd frontend
npx eslint .              # expect 0 errors, 0 warnings
npx tsc --noEmit -p tsconfig.json   # expect no output
npm run build              # expect "Compiled successfully" and a route table
```

## 11. Backend static verification (no server needed)

```bash
cd backend
python3 -m compileall -q app/     # expect exit code 0, no output
python3 -m pyflakes app/          # expect no output
```

## 12. Full Docker stack (requires Docker + optionally an AMD GPU)

```bash
cp .env.example .env
docker compose -f docker-compose.amd.yml up -d
docker compose -f docker-compose.amd.yml ps    # all services should show healthy/running
```

See `DEPLOYMENT.md` for what is and isn't independently verifiable without a real Docker daemon / AMD GPU.
