# Hackathon Presentation

## 2-minute demo script

> "This is CareSyncAI — a telemedicine platform where a patient's consultation isn't reviewed by one AI model, it's reviewed by 17 specialized agents working in real time, the same way a hospital has separate specialists for triage, diagnosis, treatment, and insurance.

> [Start a demo consultation] Here's a patient with chest pain. Watch the agent panel — Symptom Agent, Diagnostic Agent, and Medical Research Agent are running concurrently right now, not one after another. Medical Research is pulling real guideline evidence through a hybrid retrieval system — dense embeddings plus keyword search — so every recommendation carries a citation, not just an assertion.

> Here's the part I'm proudest of: this red flag [point to escalation] came from our Hallucination Detection agent, which independently reviews every other agent's claims for missing evidence — and our vision pipeline, which just read the patient's posture and facial expression as a pain signal and fed that into the same consensus score as the text-based agents.

> Everything runs free-tier by default — no OpenAI or Anthropic key required — with an AMD ROCm GPU path for when you want to scale it up. That's CareSyncAI."

## 5-minute demo script

Add to the above:
1. **Show the Agent Insights Panel** (Consensus Timeline tab) — walk through the 8 execution batches, point out those aren't scripted, they're a live topological sort of a dependency graph.
2. **Switch to the Memory tab** — show the shared-fact scratchpad agents wrote to each other during the run, and (if a returning patient) the semantic-search hit from a prior visit.
3. **Switch to the RAG tab** — type a live query, show the hybrid score bar and the citation list.
4. **Show the GPU dashboard** — explain the ROCm→CUDA→CPU auto-detection and that this demo is currently running on [CPU/ROCm, whichever is true].
5. **Export a report as PDF** — show it's a real generated PDF, not a screenshot.

## 10-minute technical walkthrough

Cover, in order:
1. **Problem framing** (see `SYSTEM_DESIGN.md` §Problem statement) — one-model answers don't show their work; multi-agent decomposition does.
2. **The 17-agent dependency graph** — draw or show `docs/ARCHITECTURE.md` diagram 4; explain batches run concurrently, not sequentially.
3. **The safety layer specifically**: Evidence → Hallucination Detection → Quality Assurance → Consensus Moderator → Escalation. Emphasize this is a *chain*, each one gates the next, ending in a single `requires_doctor_review` boolean the frontend can't bypass.
4. **RAG**: show `docs/ARCHITECTURE.md` diagram 8 — dense+BM25 hybrid, why hybrid (exact terminology vs. semantic paraphrase), the PubMed live-lookup path, and the grounding validator.
5. **Vision as a consensus participant, not a UI toy** — show `ConsensusEngine.build_consensus`'s `vision_observation` parameter live in code if asked; a high pain/distress signal from camera alone can flip `requires_doctor_review` to `true`.
6. **GPU/ROCm**: `torch.version.hip` detection trick, why it lets one code path serve AMD and NVIDIA identically, `InferenceScheduler`'s micro-batching for when an LLM upgrade path is added.
7. **Everything free-tier by default** — walk through one fallback chain live (e.g. stop Redis, show the log line, show the app keep working).
8. **What's honestly not done yet** — see `SYSTEM_DESIGN.md` §Limitations and the audit report. Judges respect an accurate limitations section more than a claim of completeness that cracks under a follow-up question.

## Demo environment notes

- If running fully offline/CPU-only, say so proactively — it's a feature ("this laptop right now has zero external services running and every subsystem still works") not a caveat to hide.
- Have `docs/DEMO_SCRIPT.md` open on a second screen for the exact click sequence if nerves hit.
