# VARUNA — Team Assignments & Task Ownership
**Names.md** — Every task, every responsibility, every member. This is the ground truth.

---

## Team Members & Workstream Ownership

| # | Name | Role | Core Deliverables & Domain |
|---|---|---|---|
| **M1** | **Aryan Lomte (Lead)** | AI Systems Architect & Full RAG Lead | Multi-Agent Task DAG Orchestrator, All RAG & Vector Pipelines, Anomaly Agent, Synthesizer Agent, OpenRouter Client, API Gateway |
| **M2** | **Aditya Yadav** | Data Engineer & Backend Infrastructure Lead | Ingestion Pipeline (NetCDF HPC extraction), PostgreSQL PostGIS spatial schema, CMLRE Darwin Core Seeding |
| **M3** | **Sahil Shah** | Predictive ML & Sensor QC Lead | 7-Day Spatio-Temporal MHW Forecast Model (ConvLSTM), Deep 1D-CNN Sensor QC Autoencoder, ML Endpoints |
| **M4** | **Advay Chavan** | Frontend Full-Stack Lead | Next.js 14 Command Center HUD, Ocean Copilot Chat Panel, Live Agent DAG Graph Visualizer, 3D WebGL Globe |
| **M5** | **Netal Gupta** | Geospatial Systems & Visualization Lead | Deck.gl + Mapbox GL Situational Canvas, ARGO Fleet Trajectories, CMLRE Species Layer, Anomaly Alert Center |
| **M6** | **Kanishka Sahal** | Marine Analytics & Presentation Lead | INCOIS ⇄ CMLRE Cross-Domain Explorer, 15+ Oceanographic Plotly Charts, SIH Master Pitch Deck & Video |

---

## 🔍 Critical Codebase Flags (High-Priority Review Items)

```
┌──────────────────────────────────────┬──────────────────────┬────────────────────────────────────────────────────────────────────────┐
│ Flagged Module                       │ Assigned Member      │ Critical Finding & Required Action                                     │
├──────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ src/memory/conversation.py           │ Aryan Lomte (M1)     │ [HIGH REVIEW] Top-level `import redis` blocks imports without Redis.   │
│                                      │                      │ Action: Wrap with resilient in-process dictionary fallback.            │
├──────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ src/llm/embedder.py                  │ Aryan Lomte (M1)     │ [HIGH REVIEW] MD5 hash fallback produces orthogonal dummy vectors.     │
│                                      │                      │ Action: Wire `openrouter_client.embed_text()` to nomic-embed-text.     │
├──────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ src/chains/sql_rag_chain.py & rag_   │ Aryan Lomte (M1)     │ [HEAVY REVIEW] Stale imports from `src.llm.ollama_client`.             │
│ chain.py                             │                      │ Action: Migrate all generation paths to `src.llm.openrouter_client`.   │
├──────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ src/database/postgres.py             │ Aditya Yadav (M2)    │ [HIGH REVIEW] Missing Darwin Core DDL & PostGIS lateral spatial join.  │
│                                      │                      │ Action: Implement `init_biodiversity_schema()` & `correlate_species`.  │
├──────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ src/ingestion/pipeline.py & reader   │ Aditya Yadav (M2)    │ [HEAVY REVIEW] Verify PyArrow dimension slicing & QC bitmasking [1,2,5,8]│
│                                      │                      │ Action: Validate end-to-end against real/mock NetCDF profile arrays.   │
└──────────────────────────────────────┴──────────────────────┴────────────────────────────────────────────────────────────────────────┘
```

---

## M1 — Aryan Lomte (Team Lead & Full RAG Lead)

### Assigned Files
- `backend/src/agents/orchestrator.py` (CREATE)
- `backend/src/agents/anomaly_agent.py` (CREATE)
- `backend/src/agents/synthesizer_agent.py` (CREATE)
- `backend/src/agents/sql_gen_agent.py` (CREATE)
- `backend/src/agents/retrieval_agent.py` (CREATE)
- `backend/src/llm/openrouter_client.py` (CREATE)
- `backend/src/llm/embedder.py` (UPDATE — wire OpenRouter nomic embeddings)
- `backend/src/chains/sql_rag_chain.py` (UPDATE — migrate to OpenRouter)
- `backend/src/chains/rag_chain.py` (UPDATE — migrate to OpenRouter)
- `backend/src/database/qdrant.py` (EXTEND — 3 collections)
- `backend/src/rag/` (MAINTAIN all retrieval & re-ranking modules)
- `backend/src/memory/` (MAINTAIN conversation, temporal, and knowledge graph)
- `backend/src/api/routes.py` (EXTEND — add `/agent/chat`, `/anomalies`, `/correlate`)
- `backend/src/api/app.py` (MAINTAIN — lifespan startup events)
- `backend/src/api/ws.py` (MAINTAIN — WebSocket token streaming)
- `VARUNA.md` & `docs/` (GOVERN)

### Tasks
- [ ] **Phase 1 (Day 1)**: Build `openrouter_client.py` with async httpx, tenacity backoff, and Nemotron-Ultra 550B completions; wire cloud embedder in `embedder.py`.
- [ ] **Phase 2 (Day 2)**: Update `sql_rag_chain.py` and `rag_chain.py` to route through OpenRouter; wrap Redis in `conversation.py` with resilient in-memory fallback.
- [ ] **Phase 3 (Day 3)**: Implement `orchestrator.py` Task DAG Planner with topological dependency resolver and parallel `asyncio.gather` execution.
- [ ] **Phase 4 (Day 4)**: Build sub-agents (`sql_gen_agent.py`, `retrieval_agent.py`, `synthesizer_agent.py`) with zero-hallucination citation validation.
- [ ] **Phase 5 (Day 5)**: Implement `anomaly_agent.py` 6-hour background scanner with Hobday (2016) MHW $P_{90}$ threshold exceedance ($D \ge 5\text{d}$) and hypoxia alerts.
- [ ] **Phase 6 (Days 6–10)**: Connect API routes, lead system integration tests, performance profiling, and hackathon defense.

---

## M2 — Aditya Yadav (Backend & Data Infrastructure Lead)

### Assigned Files
- `backend/src/database/postgres.py` (EXTEND — add biodiversity DDL & lateral join)
- `backend/src/ingestion/seed_biodiversity.py` (CREATE — seed 500+ Darwin Core records)
- `backend/src/ingestion/pipeline.py` (MAINTAIN — batch COPY buffer)
- `backend/src/ingestion/netcdf_reader.py` (MAINTAIN — PyArrow NetCDF extractor)
- `backend/src/database/duckdb_client.py` (MAINTAIN — Parquet analytics)
- `backend/src/utils/geo.py` (MAINTAIN — bounding boxes and city lookups)

### Tasks
- [ ] **Phase 1 (Day 1–2)**: Implement `init_biodiversity_schema()` in `postgres.py` with Darwin Core columns and PostGIS GIST spatial indexes.
- [ ] **Phase 2 (Day 2–3)**: Build `seed_biodiversity.py` with 500+ verified Indian Ocean species records (*Sardinella*, *Rastrelliger*, *Acropora*, *Thunnus*, *Dugong*).
- [ ] **Phase 3 (Day 3–4)**: Implement `correlate_species_with_ocean()` lateral join ($\le 50\text{km}, \le 7\text{d}$) and `get_species_near_float()`.
- [ ] **Phase 4 (Day 4–5)**: Validate NetCDF extraction against real ARGO NetCDF files ensuring QC bitmasking `[1, 2, 5, 8]`.

---

## M3 — Sahil Shah (Predictive ML & Deep Sensor QC Lead)

### Assigned Files
- `backend/src/ml/mhw_forecast.py` (CREATE — 7-day MHW spatio-temporal predictive model)
- `backend/src/ml/qc_autoencoder.py` (CREATE — 1D-CNN float sensor QC autoencoder)
- `backend/src/ml/__init__.py` (CREATE)
- `backend/tests/test_ml_models.py` (CREATE — ML unit tests)

### Tasks
- [ ] **Phase 1 (Day 1–2)**: Define Pydantic request/response schemas for ML endpoints and initialize `src/ml/`.
- [ ] **Phase 2 (Day 2–3)**: Implement 1D-CNN Autoencoder in `qc_autoencoder.py` to scan vertical ARGO profiles ($0-2000\text{m}$) for sensor drift and biofouling.
- [ ] **Phase 3 (Day 3–4)**: Implement 7-day spatio-temporal MHW predictive forecasting model in `mhw_forecast.py` over Indian Ocean 2°x2° grids.
- [ ] **Phase 4 (Day 5–7)**: Connect ML endpoints (`/api/v1/ml/forecast-mhw`, `/api/v1/ml/qc-detect`) into FastAPI router and validate inference latency ($< 100\text{ms}$).

---

## M4 — Advay Chavan (Frontend Full-Stack Lead)

### Assigned Files
- `frontend/app/page.tsx` (EXTEND — VARUNA rebrand & 4-view operational switch)
- `frontend/components/ChatPanel.tsx` (EXTEND — Agentic mode toggle & SQL drawer)
- `frontend/components/AgentGraph.tsx` (CREATE — Live Task DAG visualizer)
- `frontend/hooks/useChatStream.ts` (EXTEND — Agent trace streaming)
- `frontend/components/ui/DockNav.tsx` (EXTEND — Alerts & Biodiversity icons)
- `frontend/components/Globe/OceanGlobe.tsx` (MAINTAIN — 3D WebGL Globe)

### Tasks
- [ ] **Phase 1 (Day 1–2)**: Rebrand `page.tsx` to **VARUNA — Marine Ecosystem Intelligence Platform**; wire 4 operational modes (`MAP`, `ANALYSIS`, `ALERTS`, `BIODIVERSITY`).
- [ ] **Phase 2 (Day 2–3)**: Build `AgentGraph.tsx` with animated Framer Motion DAG execution tree, duration badges, and status pulses.
- [ ] **Phase 3 (Day 3–4)**: Upgrade `ChatPanel.tsx` with `<> Show Generated SQL` inspectable drawer and zero-hallucination provenance badges `[WMO: 1902303 | Row #14]`.

---

## M5 — Netal Gupta (Geospatial Systems & Visualization Lead)

### Assigned Files
- `frontend/components/OceanMap.tsx` (EXTEND — vertical depth slider & species layer)
- `frontend/components/AnomalyAlerts.tsx` (CREATE — early-warning situational room)
- `frontend/components/Map/TrajectoryLayer.tsx` (MAINTAIN — 90-day drift vectors)
- `frontend/components/Map/FloatMap.tsx` (MAINTAIN — float marker popups)

### Tasks
- [ ] **Phase 1 (Day 1–3)**: Build `AnomalyAlerts.tsx` with Hobday MHW curves, severity gauges, vulnerable species impact badges, and 1-click fisheries advisory export.
- [ ] **Phase 2 (Day 3–5)**: Implement vertical depth scrubber slider ($0-2000\text{m}$) and toggleable CMLRE species Deck.gl `ScatterplotLayer` on `OceanMap.tsx`.

---

## M6 — Kanishka Sahal (Marine Analytics & Presentation Lead)

### Assigned Files
- `frontend/components/CrossDomainExplorer.tsx` (CREATE — INCOIS ⇄ CMLRE Explorer)
- `frontend/components/Charts/` (COMPLETE ALL 15 CHART MODULES)
  - `CrossCorrelogram.tsx` (FILL STUB — $5\times 5$ correlation matrix)
  - `ObsDensityMap.tsx` (FILL STUB — observation density grid)
  - `ProfileCount.tsx` (FILL STUB — monthly profile count bar chart)
  - `QCHistogram.tsx` (FILL STUB — sensor QC flag distribution)
- SIH 9-Slide Master Deck & 5-min Demo Video Narration (CREATE)

### Tasks
- [ ] **Phase 1 (Day 1–3)**: Build `CrossDomainExplorer.tsx` with environmental thermal envelopes ($22-26^\circ\text{C}$ vs observed $29.2^\circ\text{C}$) and correlated observation table.
- [ ] **Phase 2 (Day 3–4)**: Fill empty chart stubs (`CrossCorrelogram.tsx`, `ObsDensityMap.tsx`, `ProfileCount.tsx`, `QCHistogram.tsx`).
- [ ] **Phase 3 (Day 4–5)**: Author official 9-slide SIH deck and record 5-minute screen demonstration video following Master Guide Section 10 & 11.

---

## Complete Blueprint References
- [docs/assignments/Aryan_Lomte.md](file:///e:/Hackathons/floatchatai-main/docs/assignments/Aryan_Lomte.md)
- [docs/assignments/Aditya_Yadav.md](file:///e:/Hackathons/floatchatai-main/docs/assignments/Aditya_Yadav.md)
- [docs/assignments/Sahil_Shah.md](file:///e:/Hackathons/floatchatai-main/docs/assignments/Sahil_Shah.md)
- [docs/assignments/Advay_Chavan.md](file:///e:/Hackathons/floatchatai-main/docs/assignments/Advay_Chavan.md)
- [docs/assignments/Netal_Gupta.md](file:///e:/Hackathons/floatchatai-main/docs/assignments/Netal_Gupta.md)
- [docs/assignments/Kanishka_Sahal.md](file:///e:/Hackathons/floatchatai-main/docs/assignments/Kanishka_Sahal.md)
- [docs/assignments/INDEX.md](file:///e:/Hackathons/floatchatai-main/docs/assignments/INDEX.md)
