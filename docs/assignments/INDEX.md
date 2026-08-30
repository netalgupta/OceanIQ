# VARUNA Team Workstream Matrix & Responsibility Index

> **Governing Purpose**: Master operational index detailing exact review requirements, critical codebase flags, and build deliverables for every team member.

---

## 1. 🔍 Critical Codebase Flags (High-Priority Review Items)

During deep testing across the backend modules, the following high-priority flags were identified:

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

## 2. 👥 Master Team Workstream Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       VARUNA WORKSTREAM MATRIX                                             │
├───────────────────┬───────────────────────────────────────────┬─────────────────────────────────────────────┤
│ Member            │ 🔍 What to REVIEW (Existing Code)         │ 🔨 What to BUILD (New Code)                 │
├───────────────────┼───────────────────────────────────────────┼─────────────────────────────────────────────┤
│ M1: Aryan Lomte   │ • FastAPI application lifecycle (app.py)  │ • Multi-Agent Task DAG (orchestrator.py)   │
│ (Team Lead &      │ • ALL RAG & Hybrid Retrieval pipelines    │ • Proactive Anomaly Agent (anomaly_agent.py)│
│  Full AI/RAG Lead)│ • SQL Chain & RAG Chain (chains/)         │ • Provenance Synthesizer (synthesizer.py)   │
│                   │ • Redis Session Memory (conversation.py)  │ • OpenRouter Client (openrouter_client.py)  │
│                   │ • Text Embedder (embedder.py)             │ • NL→SQL Sub-Agent (sql_gen_agent.py)       │
│                   │ • Qdrant Collections (argo_knowledge/etc) │ • Retrieval Sub-Agent (retrieval_agent.py)  │
│                   │ • Observability & Tracer pipelines        │ • Gateway Routes (/agent/chat, /anomalies)  │
├───────────────────┼───────────────────────────────────────────┼─────────────────────────────────────────────┤
│ M2: Aditya Yadav  │ • NetCDF extraction (netcdf_reader.py)    │ • Darwin Core Seeder (seed_biodiversity.py) │
│ (Backend / Data)  │ • Batch Ingestion Pipeline (pipeline.py)  │ • Biodiversity Schema & GIST Spatial Index  │
│                   │ • DuckDB Parquet Reader (duckdb_client.py)│ • PostGIS Lateral Join (correlate_species)  │
├───────────────────┼───────────────────────────────────────────┼─────────────────────────────────────────────┤
│ M3: Sahil Shah    │ • Model Evaluation Benchmarks             │ • 7-Day MHW Forecast Model (mhw_forecast.py)│
│ (Predictive ML &  │ • Physical Ocean Feature Engineering      │ • 1D-CNN Sensor QC Autoencoder (qc_auto.py) │
│  Deep Sensor QC)  │ • Historical Heatwave Baseline Datasets   │ • ML Endpoints (/api/v1/ml/forecast-mhw etc)│
├───────────────────┼───────────────────────────────────────────┼─────────────────────────────────────────────┤
│ M4: Advay Chavan  │ • App Shell & HUD Overlays (page.tsx)     │ • Live Task DAG Visualizer (AgentGraph.tsx) │
│ (Frontend Full)   │ • ChatPanel message history & state       │ • Inspectable <> Show SQL Drawer            │
│                   │ • useChatStream hook response parsing     │ • Operational 4-View Switcher in DockNav    │
├───────────────────┼───────────────────────────────────────────┼─────────────────────────────────────────────┤
│ M5: Netal Gupta   │ • Deck.gl Scatterplot Canvas (OceanMap)   │ • Early-Warning Feed (AnomalyAlerts.tsx)    │
│ (Geospatial)      │ • 90-Day Drift Vectors (TrajectoryLayer)  │ • Vertical Depth Slicer (0m to 2000m)       │
│                   │ • Float Marker Popups (FloatMap.tsx)      │ • CMLRE Biodiversity Deck.gl Layer          │
├───────────────────┼───────────────────────────────────────────┼─────────────────────────────────────────────┤
│ M6: Kanishka Sahal│ • 15+ Oceanographic Charts (AnalysisHub)  │ • INCOIS ⇄ CMLRE Explorer (CrossDomain.tsx) │
│ (Analytics / Pres)│ • TSIsopycnals.tsx & HovmollerDiagram.tsx │ • Fill 4 Chart Stubs (CrossCorrelogram etc) │
│                   │ • DepthProfile.tsx & Surface3D.tsx        │ • SIH 9-Slide Pitch Deck & 5-min Demo Video │
└───────────────────┴───────────────────────────────────────────┴─────────────────────────────────────────────┘
```

---

## 3. Individual Assignment Blueprints

- [**Aryan Lomte** (Team Lead, AI Systems Architect & Full RAG Lead)](file:///e:/Hackathons/floatchatai-main/docs/assignments/Aryan_Lomte.md)
- [**Aditya Yadav** (Data Engineer & Backend Infrastructure Lead)](file:///e:/Hackathons/floatchatai-main/docs/assignments/Aditya_Yadav.md)
- [**Sahil Shah** (Predictive ML & Sensor Quality Control Lead)](file:///e:/Hackathons/floatchatai-main/docs/assignments/Sahil_Shah.md)
- [**Advay Chavan** (Frontend Full-Stack & UI Systems Lead)](file:///e:/Hackathons/floatchatai-main/docs/assignments/Advay_Chavan.md)
- [**Netal Gupta** (Geospatial Systems & Visualization Lead)](file:///e:/Hackathons/floatchatai-main/docs/assignments/Netal_Gupta.md)
- [**Kanishka Sahal** (Marine Analytics & Presentation Lead)](file:///e:/Hackathons/floatchatai-main/docs/assignments/Kanishka_Sahal.md)
