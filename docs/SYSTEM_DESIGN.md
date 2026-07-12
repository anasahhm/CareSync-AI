# CareSyncAI : System Design

## Problem statement

Telehealth triage today is either a human doctor doing everything unaided, or a single LLM prompt producing an unstructured, ungrounded, unverifiable answer. Neither scales safely: the first doesn't scale at all, the second hallucinates with no safety net. CareSyncAI premise is that **decomposing clinical reasoning into specialized, auditable agents that must show their evidence and can be overruled by a dedicated safety layer** is a more trustworthy middle ground than either extreme.

## Solution shape

A single consultation triggers 17 narrow agents (not 17 calls to one generalist LLM prompt). Each agent:
- Has one job (symptom extraction, differential diagnosis, guideline lookup, insurance pre-auth, etc.)
- Publishes structured `recommendations` (with `confidence` and `evidence`) and `escalations` (with a `level`) onto a shared event bus
- Can read what any other agent already published, via the event bus or shared memory

Three agents exist specifically to **police the other fourteen**: Evidence (checks recommendations carry support), Hallucination Detection (flags high-confidence/low-evidence claims and cross-agent contradictions), and Quality Assurance (a hard gate — did every expected agent actually run, is a diagnosis present, did hallucination review clear). A Consensus Moderator resolves ties between conflicting recommendations, and a final Escalation agent aggregates every risk signal raised all run into one `requires_doctor_review` decision. This is deliberately more conservative than a single-model answer: several independent design choices bias the system toward "flag it for a human" over "produce a confident final answer."

## Why multi-agent (vs. one large prompt)

- **Auditability**: every recommendation has a named source agent and an evidence list, so a doctor (or a future compliance reviewer) can trace *why* the system said what it said.
- **Partial failure tolerance**: if one agent throws, `agent_outputs[agent_type] = {"status": "FAILED", ...}` and the pipeline continues; a single-call architecture has no equivalent unit of failure.
- **Independent evolvability**: the dependency graph (`WorkflowCoordinator`) means adding an 18th agent is a `DEPENDENCIES` list edit, not a prompt-engineering exercise across a monolith.

Tradeoff: more moving parts, more code, and (for the *current* heuristic/rule-based agent implementations) less nuance than a strong general-purpose model would produce on a genuinely novel case. See Limitations.

## Why vision AI

Pain and distress are partially non-verbal. A gesture/pose/face/movement pipeline that turns "patient guarded their abdomen and grimaced" into `{"pain_score": 0.82, "body_part": "Abdomen", "confidence": 0.7}` gives the agents (and the consensus engine) a signal that pure chief-complaint text misses — and it's designed to be a *first-class* consensus participant, not a decorative video overlay: a high vision-derived distress signal raises `overall_risk_score` and can push `requires_doctor_review` to true on its own.

## Why RAG

A rule-based/heuristic agent asserting "obtain ECG and troponin promptly" without a citation is exactly the kind of ungrounded claim the project's own Hallucination Detection agent is designed to catch. RAG exists so that clinical claims are backed by retrieved guideline text and (optionally) PubMed literature with a citation, not by a hardcoded string the agent author happened to type in. Hybrid (dense + BM25) retrieval exists because dense embeddings alone can miss exact terminology matches (a drug name, a guideline code) that a keyword method catches reliably, and vice versa for semantic paraphrase.

## Why GPU acceleration / AMD ROCm

None of the current agents *require* a GPU — they're deterministic/heuristic, not neural. The GPU layer exists for the **future/optional** LLM-upgrade path (`PromptBuilder` + `ModelLoader`) and for embedding throughput at scale (sentence-transformers on GPU is materially faster than CPU at high query volume). AMD specifically, because this is built for AMD Developer Cloud: `DeviceManager` detects ROCm via `torch.version.hip` (ROCm builds expose the same `torch.cuda.*` API surface as NVIDIA, just with `hip` set instead of `cuda`), so the same code path serves both vendors, with CPU as the universal fallback.

## Why Ollama

"Free models only, no paid API required" was a hard project constraint. Ollama is a free, local, OpenAI-API-adjacent server for open models (Llama/Mistral/Qwen/etc.) — it's the one piece of the free-model chain that needs a running process, so every caller (`ModelLoader`, `EmbeddingService`, `AIReportService`) treats it as optional and falls back cleanly (rule-based stub, hashed embedding, deterministic heuristic respectively) when it isn't reachable.

## Why Qdrant (with FAISS fallback)

Qdrant is a free, open-source, Docker-composable vector database — a reasonable production-grade choice for the AMD Cloud deployment. FAISS in-memory is the local-dev/no-Docker fallback so `RetrievalEngine` never hard-depends on a running service.

## Key tradeoffs made

| Decision | Tradeoff accepted |
|---|---|
| Rule-based/heuristic agents (not LLM calls) by default | Faster, deterministic, zero-cost, zero-hallucination-risk for the agents themselves — but less nuanced than a strong LLM on a genuinely novel/ambiguous case. The `PromptBuilder`/`ModelLoader` seam exists specifically so any agent can be upgraded to call Ollama without changing its interface. |
| Graceful degradation everywhere (Qdrant→FAISS, Redis→dict, GPU→CPU, Ollama→stub) | More `try/except` branches and dual code paths per subsystem, in exchange for the system never hard-failing just because an optional service isn't running — verified directly in this sandbox, which has none of Redis/Qdrant/Ollama/GPU running. |
| In-memory FAISS/short-term-memory fallbacks are not persisted across restarts | Acceptable for a hackathon/local-dev fallback; Qdrant/Redis are the durable path when actually deployed via `docker-compose.amd.yml`. |
| BM25 implemented in pure Python rather than Elasticsearch | The guideline corpus is small (a curated set, not millions of docs) — Elasticsearch would be disproportionate infrastructure for the actual corpus size. |
| Vision emotion/pain detection is geometry-heuristic, not a trained classifier | CPU-cheap, dependency-free, and transparent (you can read exactly why a score was produced) — but lower accuracy ceiling than a trained model; documented as a heuristic, not oversold as "AI-powered emotion recognition" in the marketing sense. |

## Known limitations

- **Heuristic clinical reasoning, not a trained/validated medical model.** The differential-diagnosis and treatment-recommendation logic is rule-based (keyword/category matching), calibrated by the author, not trained or validated against real clinical outcomes. This is a prototype decision-support aid, not a diagnostic device.
- **Guideline corpus is small and curated**, not a full indexed WHO/CDC/PubMed corpus. `GuidelineRetriever`'s seed set is illustrative.
- **Vision detectors are heuristic geometry**, not trained emotion/pain-classification models — see the tradeoff table above.
- **PubMed retrieval requires outbound internet access** to `eutils.ncbi.nlm.nih.gov`; it fails closed (returns no results) if unreachable, which is expected behavior in network-restricted environments.
- **No production security hardening pass has been completed** (see the audit report for specifics on what's in place vs. what would need attention before real patient data touches this system).
- **No automated test suite exists yet.** Verification in this project has been manual/interactive (see `RUNBOOK.md`), not CI-enforced.

## Future work

- Wire `PromptBuilder`/`ModelLoader` into one or more agents as an actual LLM-backed reasoning path (currently built but unused — a deliberate "seam," not a half-finished feature).
- Replace the curated guideline corpus with a real indexed WHO/CDC/PubMed ingestion pipeline.
- Add a trained (not heuristic) vision emotion/pain model behind the same `EmotionDetector`/`PainDetector` interfaces.
- Automated test suite (unit + integration) and CI.
- Formal security review (see audit report) before any real patient data.
