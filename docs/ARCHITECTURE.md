# CareSyncAI V2 — Architecture

All diagrams are plain Mermaid (no color styling) so they render legibly on GitHub, in most Markdown viewers, and export cleanly to PNG/SVG via `mmdc` (`@mermaid-js/mermaid-cli`) if a static image is needed for slides.

## 1. Overall System Architecture

```mermaid
flowchart TB
    subgraph Client
        FE[Next.js 15 Frontend]
    end

    subgraph Backend["FastAPI Backend"]
        API[REST API Layer]
        WS[Socket.IO Server]
        ORCH[ConsultationOrchestrator]
        AGENTS[17 Agents]
        CONS[ConsensusEngine]
    end

    subgraph Data["Data & AI Services"]
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        QDRANT[(Qdrant / FAISS fallback)]
        OLLAMA[Ollama / free LLM]
        GPU[GPU Layer: ROCm/CUDA/CPU]
    end

    FE -->|HTTPS REST| API
    FE <-->|WebSocket| WS
    API --> ORCH
    WS --> ORCH
    ORCH --> AGENTS
    AGENTS --> CONS
    CONS --> ORCH
    ORCH --> PG
    AGENTS -->|memory| REDIS
    AGENTS -->|retrieval| QDRANT
    AGENTS -->|free-model calls| OLLAMA
    OLLAMA --> GPU
```

## 2. Backend Architecture

```mermaid
flowchart LR
    subgraph API["api/routes"]
        AUTH[auth]
        CONSULT[consultations]
        VIDEO[video]
        GPUR[gpu]
        MEM[memory]
        RAGR[rag]
        REP[reports]
        METR[metrics]
    end

    subgraph Services
        AGENTSVC[AgentService\nlifecycle owner]
    end

    subgraph Core["orchestration / communication"]
        REG[AgentRegistry]
        WFC[WorkflowCoordinator]
        ORCH2[ConsultationOrchestrator]
        CE[ConsensusEngine]
        ES[EventStore]
        BUS[AgentCommunicationLayer\nEvent Bus]
    end

    API --> AGENTSVC
    AGENTSVC --> REG
    AGENTSVC --> ORCH2
    AGENTSVC --> VISIONMGR[VisionManager]
    AGENTSVC --> RAGMGR[RAGManager]
    AGENTSVC --> MEMMGR[MemoryManager]
    AGENTSVC --> GPUMGR[GPUManager]
    REG --> BUS
    ORCH2 --> WFC
    ORCH2 --> CE
    ORCH2 --> ES
    ORCH2 --> BUS
```

## 3. Frontend Architecture

```mermaid
flowchart TB
    ROOT[layout.tsx] --> ERR[ErrorBoundary]
    ERR --> PROV[Providers: QueryClient + NotificationProvider]
    PROV --> PAGES[App Router Pages]

    PAGES --> DASH[DoctorDashboard / PatientDashboard]
    PAGES --> ROOM["ConsultationRoom [roomId]"]

    ROOM --> WEBRTC[WebRTC video]
    ROOM --> SOCKHOOK[useConsultationSocket]
    ROOM --> ANNOT[AnnotationLayer]
    ROOM --> VISPANEL[VisionPanel]
    ROOM --> REPMODAL[Report Modal]

    REPMODAL --> RV[ReportViewer]
    RV --> INSIGHTS[AgentInsightsPanel\ndoctor-only]
    INSIGHTS --> TL[ConsensusTimeline]
    INSIGHTS --> MEMV[MemoryVisualization]
    INSIGHTS --> RAGV[RAGVisualization]

    DASH --> GPUDASH[GPUDashboard]
```

## 4. Multi-Agent Architecture (17 agents, 8 dependency batches)

```mermaid
flowchart TB
    B1["Batch 1: Chief Orchestrator, Clinical Review,\nCompliance & Privacy, Insurance Verification, Symptom"]
    B2["Batch 2: Diagnostic, Medical History, Triage Escalation"]
    B3["Batch 3: Evidence, Medical Research, Treatment Recommendation"]
    B4["Batch 4: Hallucination Detection"]
    B5["Batch 5: Quality Assurance"]
    B6["Batch 6: Consensus Moderator"]
    B7["Batch 7: Escalation, Explanation"]
    B8["Batch 8: Followup Coordination"]

    B1 --> B2 --> B3 --> B4 --> B5 --> B6 --> B7 --> B8
```

Each batch runs its agents **concurrently** (`asyncio.gather`); batches run sequentially because later batches depend on earlier agents' published recommendations. The dependency graph is computed by `WorkflowCoordinator` via topological sort — adding/removing an agent only requires updating its `DEPENDENCIES` list.

## 5. Vision Pipeline

```mermaid
flowchart LR
    CAM[Camera frame\nJPEG upload] --> PRE[Preprocessing\nresize + CLAHE]
    PRE --> GEST[Gesture Detector\nMediaPipe Hands]
    PRE --> POSE[Pose Detector\nMediaPipe Pose]
    PRE --> FACE[Face Detector\nMediaPipe FaceMesh]
    FACE --> EMO[Emotion Detector\nheuristic geometry]
    POSE --> MOV[Movement Detector\nlandmark displacement]
    EMO --> PAIN[Pain Detector]
    POSE --> PAIN
    MOV --> PAIN
    GEST --> FUSION[Multimodal Fusion]
    POSE --> FUSION
    FACE --> FUSION
    EMO --> FUSION
    MOV --> FUSION
    PAIN --> FUSION
    FUSION --> OBS["VisionObservation\n{pain_score, body_part, confidence, distress_flags}"]
    OBS --> EVENTBUS[Event Bus: VISION_OBSERVATION]
    OBS --> SHAREDMEM[Shared Memory]
```

## 6. Speech Pipeline

```mermaid
flowchart LR
    AUDIO[WAV clip upload] --> CHECK{librosa\ninstalled?}
    CHECK -->|yes| PITCH[Pitch tracking + RMS energy\nlibrosa.pyin]
    CHECK -->|no| FALLBACK[stdlib wave module\nRMS energy only]
    PITCH --> CLASSIFY[Heuristic classification:\ndistressed / flat / calm]
    FALLBACK --> CLASSIFY
    CLASSIFY --> MERGE[Merged into latest\nVisionObservation]
```

## 7. GPU / ROCm Architecture

```mermaid
flowchart TB
    START[DeviceManager init] --> CHECK1{torch installed?}
    CHECK1 -->|no| CPU[backend = cpu]
    CHECK1 -->|yes| CHECK2{torch.cuda.is_available?}
    CHECK2 -->|no| CPU
    CHECK2 -->|yes| CHECK3{torch.version.hip set?}
    CHECK3 -->|yes| ROCM[backend = rocm]
    CHECK3 -->|no| CUDA[backend = cuda]

    ROCM --> METRICS[GPUMetrics: rocm-smi]
    CUDA --> METRICS2[GPUMetrics: nvidia-smi]
    CPU --> METRICS3[GPUMetrics: cpu note]

    ROCM --> SCHED[InferenceScheduler\ndynamic micro-batching]
    CUDA --> SCHED
    CPU --> SCHED

    SCHED --> LOADER[ModelLoader]
    LOADER --> OLLAMACHECK{Ollama reachable?}
    OLLAMACHECK -->|yes| OLLAMAGEN[Free local generation]
    OLLAMACHECK -->|no| STUBGEN[Deterministic stub result]
```

## 8. RAG Architecture

```mermaid
flowchart TB
    QUERY[Query / claim text] --> EMB[EmbeddingService\nsentence-transformers -> Ollama -> hashed fallback]
    EMB --> CACHE[CachedEmbeddingService\nRedis + in-process]
    CACHE --> VSTORE[VectorStore\nQdrant -> FAISS fallback]
    QUERY --> BM25[BM25Index]
    VSTORE --> HYBRID[Hybrid Reranker\n0.65 dense + 0.35 BM25]
    BM25 --> HYBRID
    HYBRID --> RESULTS[Ranked results]
    RESULTS --> CITE[CitationEngine]
    RESULTS --> VALID[RecommendationValidator\ngrounding score]

    PUBMED[PubMedRetriever\nNCBI E-utilities] --> EVIDENCE[EvidenceRetriever]
    RESULTS --> EVIDENCE
    EVIDENCE --> AGENTS2[MedicalResearchAgent\nEvidenceAgent]
```

## 9. Memory Architecture

```mermaid
flowchart TB
    subgraph ShortTerm["Short-term (per consultation)"]
        CM[ConsultationMemory\nturns + agent outputs, capped]
        SM[SharedMemory\ncross-agent scratchpad]
    end

    subgraph LongTerm["Long-term (per patient)"]
        PM[PatientMemory\nDB history]
        SEM[SemanticMemory\nembedding similarity search, capped]
    end

    REDIS[(Redis\nauto in-process fallback)] --> CM
    REDIS --> SM
    PG[(PostgreSQL)] --> PM
    PM --> SEM

    AGENTS3[Agents] --> CM
    AGENTS3 --> SM
    ORCH3[Orchestrator] --> PM
```

## 10. Consensus Engine

```mermaid
flowchart TB
    OUT[All agent outputs\nrecommendations + escalations] --> WEIGHT[Weighted voting\nconfidence x agent confidence]
    VISION2[Vision observation] --> WEIGHT
    MOD[Moderator rulings] --> BOOST[Boost chosen claim\ndemote alternatives]
    WEIGHT --> BOOST
    HALLU[Hallucination/QA gate penalty] --> PENALTY[Confidence penalty 0.8x-0.85x]
    BOOST --> PENALTY
    PENALTY --> SCORE["consensus_score = (agents_completed / total) x avg_confidence"]
    SCORE --> RISK[overall_risk_score\nfrom escalation levels]
    RISK --> REVIEW{risk > 0.6 or\nconflicts or\nhallucination flagged?}
    REVIEW -->|yes| DOCTOR[requires_doctor_review = true]
    REVIEW -->|no| AUTO[Auto-finalized]
```

## 11. Consultation Lifecycle

```mermaid
sequenceDiagram
    participant P as Patient/Doctor (FE)
    participant API as REST API
    participant ORCH as Orchestrator
    participant AG as 17 Agents
    participant CE as ConsensusEngine
    participant DB as PostgreSQL

    P->>API: POST /consultations (create)
    P->>API: POST /agents/process/{id}
    API->>ORCH: process_consultation()
    loop 8 batches
        ORCH->>AG: execute concurrently per batch
        AG-->>ORCH: recommendations, escalations
        ORCH->>DB: persist AgentEventLog (best-effort)
    end
    ORCH->>CE: build_consensus()
    CE-->>ORCH: consensus dict
    ORCH->>DB: persist AgentProcessingReport, AgentConsensus
    ORCH-->>API: result
    API-->>P: consensus + recommendations
    P->>API: GET /reports/{id}/export/{format}
```

## 12. Database ER Diagram (core tables)

```mermaid
erDiagram
    USER ||--o{ CONSULTATION : "doctor/patient"
    CONSULTATION ||--o| AGENT_PROCESSING_REPORT : has
    AGENT_PROCESSING_REPORT ||--o{ AGENT_EVENT_LOG : contains
    AGENT_PROCESSING_REPORT ||--o{ AGENT_RECOMMENDATION : contains
    AGENT_PROCESSING_REPORT ||--o{ ESCALATION_EVENT : contains
    AGENT_PROCESSING_REPORT ||--o| AGENT_CONSENSUS : has
    CONSULTATION ||--o| AI_REPORT : has
    CONSULTATION ||--o{ ANNOTATION : has
    CONSULTATION ||--o{ GESTURE_EVENT : has
    USER ||--o| DOCTOR_PROFILE : has
    USER ||--o| PATIENT_PROFILE : has
```

## 13. API Flow Diagram

```mermaid
flowchart LR
    FE2[Frontend] -->|JWT Bearer| AUTH2["/api/auth/*"]
    FE2 --> CONSULT2["/api/consultations/*"]
    FE2 --> VIDEO2["/api/video/*"]
    FE2 --> GPU2["/api/gpu/*"]
    FE2 --> MEM2["/api/memory/*"]
    FE2 --> RAG2["/api/rag/*"]
    FE2 --> REP2["/api/reports/*"]
    FE2 --> AGENTS4["/api/agents/*"]
    PROM[Prometheus] -->|scrape, no auth| METRICS2["/metrics"]
```

## 14. Docker Architecture (AMD compose)

```mermaid
flowchart TB
    NGINX[nginx: 80/443] --> FE3[frontend: 3000]
    NGINX --> BE[backend: 8000, Dockerfile.amd]
    BE --> PG2[(postgres:5432)]
    BE --> REDIS2[(redis:6379)]
    BE --> QDRANT2[(qdrant:6333)]
    BE --> OLLAMA2[ollama:11434]
    CELERY[celery_worker, same image as backend] --> REDIS2
    CELERY --> PG2
    PROM2[prometheus:9090] --> BE
    GRAFANA[grafana:3001] --> PROM2
    BE -.->|/dev/kfd, /dev/dri| GPU3[AMD GPU]
    OLLAMA2 -.->|/dev/kfd, /dev/dri| GPU3
```

## 15. Deployment Architecture (AMD Developer Cloud)

```mermaid
flowchart TB
    subgraph Cloud["AMD Developer Cloud instance"]
        subgraph Compose["docker compose -f docker-compose.amd.yml"]
            SVC[All services from diagram 14]
        end
        GPU4[AMD GPU via ROCm]
    end
    USER2[Judge / User browser] -->|HTTPS| Cloud
```

No Kubernetes, no Helm, no Terraform anywhere in this deployment — Docker Compose only, by explicit project requirement.

## 16. Authentication Flow

```mermaid
sequenceDiagram
    participant FE4 as Frontend
    participant AUTH3 as /api/auth
    participant DB2 as PostgreSQL

    FE4->>AUTH3: POST /login {email, password}
    AUTH3->>DB2: verify password hash
    AUTH3-->>FE4: access_token (short-lived) + refresh_token
    FE4->>AUTH3: (later) POST /refresh {refresh_token}
    AUTH3->>DB2: validate stored refresh token hash
    AUTH3-->>FE4: new access_token
    Note over FE4: axios interceptor auto-refreshes\non 401 and retries the original request
```

## 17. Report Generation Flow

```mermaid
flowchart TB
    TRIGGER[Consultation ends] --> GEN[AIReportService.generate_report]
    GEN --> HASLLM{Paid LLM\nconfigured?}
    HASLLM -->|yes| PAID[Anthropic/OpenAI call]
    PAID -->|fails| FREE[Free path: ModelLoader/Ollama]
    HASLLM -->|no| FREE
    FREE -->|unreachable| STUB[Minimal stub report]
    PAID -->|success| PARSE[Parse structured JSON]
    FREE -->|success| PARSE
    PARSE --> SAVE[(AIReport row)]
    SAVE --> EXPORT[/api/reports/id/export/pdf|md|json]
```

## 18. WebSocket Flow

```mermaid
sequenceDiagram
    participant FE5 as Frontend
    participant SIO as Socket.IO server
    participant BUS2 as Event Bus

    FE5->>SIO: connect + join_consultation
    BUS2-->>SIO: agent_started / agent_completed / consensus_update
    SIO-->>FE5: emit agent:* events
    FE5->>FE5: AgentCoordinationDashboard renders live
    Note over FE5,SIO: reconnection handled by socket.io-client\n(reconnection: true, backoff 1s-5s, 5 attempts)
```

## 19. Event Bus Diagram

```mermaid
flowchart LR
    PUB[Any agent / VisionManager / ConsensusEngine] -->|publish AgentEvent| LOCALBUS[LocalEventBus\nin-process pub/sub]
    LOCALBUS --> SUBSCRIBERS[Subscribers:\nSocket.IO bridge, EventStore ring buffer]
    LOCALBUS --> HISTORY[get_event_history\nreplayed by agents + /agents/timeline]
    EVENTSTORE[EventStore] -->|best-effort persist| PGLOG[(AgentEventLog table)]
```

## 20. Complete Component Dependency Diagram

```mermaid
flowchart TB
    AGENTSVC2[AgentService] --> REG2[AgentRegistry] --> AGENTS5[17 Agent instances]
    AGENTSVC2 --> MEMMGR2[MemoryManager] --> REDISCACHE[RedisCache]
    AGENTSVC2 --> RAGMGR2[RAGManager] --> RETRIEVAL[RetrievalEngine]
    AGENTSVC2 --> VISIONMGR2[VisionManager] --> CAMMGR[CameraManager]
    AGENTSVC2 --> GPUMGR2[GPUManager] --> DEVMGR[DeviceManager]

    AGENTS5 -.->|self.rag| RAGMGR2
    AGENTS5 -.->|self.vision| VISIONMGR2
    ORCH4[ConsultationOrchestrator] -.->|memory_manager| MEMMGR2
    ORCH4 --> AGENTS5
    ORCH4 --> CE2[ConsensusEngine]
```
