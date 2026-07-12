# Judge Q&A

Direct answers to the questions this system is most likely to get. Where the honest answer is a limitation, it's stated as one — see `SYSTEM_DESIGN.md` for the full limitations list.

**Q: How does the system work end to end during a consultation?**
A: Patient/doctor create a consultation → the 17-agent pipeline runs in 8 dependency-ordered batches (concurrent within a batch) → each agent publishes recommendations/escalations with confidence and evidence to a shared event bus → the Consensus Engine does weighted scoring, folds in the Consensus Moderator's tie-breaks and the vision pipeline's observation, and produces a final consensus with a `requires_doctor_review` flag → a report is generated (free Ollama path or paid Anthropic/OpenAI, whichever is configured) → exportable as PDF/Markdown/JSON.

**Q: Why is this innovative rather than "ChatGPT with extra steps"?**
A: The agents are independently-scoped and adversarial to each other by design: Hallucination Detection and Quality Assurance exist specifically to catch and gate the other agents' output, not to add more generated text. That's a structural difference from a single prompt, not a cosmetic one — a single-model answer has no equivalent internal check.

**Q: Why AMD GPUs specifically?**
A: Built for AMD Developer Cloud. `DeviceManager` detects ROCm via `torch.version.hip` (ROCm PyTorch builds expose the same `torch.cuda.*` API as NVIDIA, just with `hip` set instead of `cuda`), so one code path serves both vendors, with CPU as a universal fallback. Honest caveat: no current agent *requires* GPU acceleration (they're rule-based, not neural) — the GPU layer's real payoff is embedding throughput at scale and the LLM-upgrade path (see below).

**Q: How does GPU acceleration actually help this specific system?**
A: Two concrete paths: (1) `sentence-transformers` embedding generation for RAG is materially faster on GPU at higher query volume, and (2) `ModelLoader`/`InferenceScheduler` (dynamic micro-batching) are the seam for upgrading any agent from heuristic to LLM-backed reasoning, where GPU inference throughput matters directly.

**Q: How does vision work, and is it just a webcam overlay?**
A: MediaPipe hand/pose/face landmarks → heuristic geometry (not a trained classifier) for emotion/posture/movement → fused into one `pain_score`/`body_part`/`distress_flags` observation → published to shared memory and the event bus → `ConsensusEngine.build_consensus` accepts it as a direct weighted input, so a strong distress signal from camera alone can raise `overall_risk_score` and flip `requires_doctor_review`. Honest caveat: the emotion/pain detectors are calibrated heuristics, not trained/validated classifiers — see limitations.

**Q: How does speech analysis work?**
A: Prosodic heuristic (pitch variance via `librosa.pyin` if installed, RMS energy variance always) classifying calm/distressed/flat — not speech-to-text, and not a trained emotion-recognition model.

**Q: How do the agents actually "collaborate," concretely?**
A: Three real mechanisms, not just "they all run": (1) later agents read earlier agents' published recommendations from the event history (e.g. Diagnostic reads Symptom's categories), (2) `SharedMemory` lets any agent write/read a named fact regardless of execution order, (3) `ConsensusModeratorAgent` explicitly resolves conflicting claims between agents in the same category before final scoring.

**Q: How does RAG work?**
A: Hybrid retrieval — dense embeddings (sentence-transformers → Qdrant/FAISS) plus BM25 keyword scoring, min-max normalized and combined (0.65/0.35 weighting), plus live PubMed lookup via NCBI's free E-utilities API. Every hit carries a citation via `CitationEngine`; `RecommendationValidator` scores how well a claim is actually grounded in retrieved evidence (term overlap, not an LLM judge). Honest caveat: the guideline corpus is a small curated seed set, not a full indexed WHO/CDC/PubMed corpus.

**Q: How does memory work?**
A: Three tiers — `ConsultationMemory` (short-term, per-visit, capped at 200 turns to bound growth), `SharedMemory` (cross-agent scratchpad for the current run), `PatientMemory`+`SemanticMemory` (long-term, per-patient, embedding-similarity search over past visit summaries, capped at 200 entries per patient). Redis-backed with automatic in-process fallback if Redis isn't running.

**Q: How does consensus actually get computed — is it just an average?**
A: Weighted by each agent's own confidence times its recommendation confidence, then: moderator rulings boost/demote conflicting claims, a hallucination/QA penalty (0.8-0.85x) reduces overall confidence if either safety gate flagged issues, and `overall_risk_score` is computed independently from escalation levels (not folded into the confidence average) — so a high-confidence but high-risk case still gets flagged.

**Q: Is this production-ready?**
A: No, and we say so directly — see the Repository Audit Results in the final report for what's verified vs. not, and `SYSTEM_DESIGN.md` for known limitations (heuristic-not-trained clinical logic, small guideline corpus, no automated test suite, no completed security hardening pass). It's a working, honestly-scoped hackathon prototype with a real architecture underneath it, not a finished clinical product.

**Q: Why should I trust any of the "verified" claims in your docs?**
A: Because we separated them explicitly: "verified by execution" means we actually ran it in this environment and observed the result; "verified by static analysis" means syntax/type/import checks passed but the behavior wasn't executed; "requires Docker/GPU/production" means neither this system nor its authors have claimed to test it, because the sandbox this was built in has no Docker daemon and no AMD GPU. That distinction is itself part of the engineering discipline we're presenting.

**Q: What would you build next with more time?**
A: See `SYSTEM_DESIGN.md` §Future work — in priority order: wire an actual LLM-backed agent through the already-built `PromptBuilder`/`ModelLoader` seam, real guideline corpus ingestion, a trained (not heuristic) vision model, and an automated test suite with CI.
