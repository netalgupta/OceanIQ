# VARUNA — Architecture Documentation

## 1. System Architecture

### 1.1 Multi-Agent Task DAG

The core differentiator over OceanIQ: compound queries are decomposed into a directed acyclic graph
of sub-agent tasks, executed in dependency order, and merged by a Synthesizer agent.

`
Query: "Compare BGC in Arabian Sea last 6mo vs equator + show affected species"

PLANNER generates:
  Task t1: SQL_GEN   -- "BGC Arabian Sea last 6 months" --> SQL + rows
  Task t2: SQL_GEN   -- "BGC equatorial Indian Ocean last 6 months" --> SQL + rows
  Task t3: BIODIVERSITY [deps: t1] -- species near Arabian Sea result coordinates
  Task t4: SYNTHESIZER [deps: t1, t2, t3] -- merge + write cited answer
`

### 1.2 Component Interactions

Backend (FastAPI, port 8000)
  |--- routes.py /api/v1/chat         --> sql_rag_chain (single-shot, backward compat)
  |--- routes.py /api/v1/agent/chat   --> agents/orchestrator.py (multi-agent DAG)
  |--- routes.py /api/v1/anomalies    --> anomaly_alerts table (read-only)
  |--- routes.py /api/v1/biodiversity --> marine_biodiversity table
  |--- routes.py /api/v1/correlate    --> cross-domain join query
  |--- ws.py      /ws                 --> WebSocket streaming for real-time chat

Frontend (Next.js, port 3000)
  |--- page.tsx (MAP | ANALYSIS | ALERTS | BIODIVERSITY tabs)
  |--- ChatPanel.tsx -> useChatStream.ts -> /api/v1/agent/chat
  |--- AnomalyAlerts.tsx -> /api/v1/anomalies (polls every 5min)
  |--- OceanMap.tsx -> /api/v1/floats + /api/v1/biodiversity
  |--- CrossDomainExplorer.tsx -> /api/v1/correlate

### 1.3 Data Architecture

Physical Ocean Data Layer:
  INCOIS/IFREMER FTP -> NetCDF files -> netcdf_reader.py -> PyArrow Table
  -> Parquet (archive) + PostgreSQL marine_data (live query) + Qdrant argo_knowledge (semantic)

Biodiversity Data Layer:
  OBIS / GBIF API -> Darwin Core JSON -> seed_biodiversity.py
  -> PostgreSQL marine_biodiversity + Qdrant bio_knowledge

Cross-Domain Fusion Layer:
  marine_data x marine_biodiversity via PostGIS ST_DWithin spatial join
  Temporal window: ±7 days | Spatial window: ≤50km radius

Anomaly Detection Layer:
  marine_data rolling statistics -> anomaly_alerts table -> /api/v1/anomalies

---

## 2. Agent Architecture

### 2.1 Planner / Orchestrator (orchestrator.py)

Input:  query (str), history (list[dict])
Output: ExecutionPlan (pydantic model)

`python
class Task(BaseModel):
    id: str                    # e.g. "t1"
    agent: str                 # SQL_GEN | RETRIEVAL | BIODIVERSITY | SYNTHESIZER
    params: dict               # agent-specific inputs
    deps: list[str]            # task IDs this task depends on

class ExecutionPlan(BaseModel):
    query: str
    tasks: list[Task]
    estimated_steps: int
`

Execution loop:
  1. Call OpenRouter Nemotron with task-decomposition system prompt
  2. Parse JSON response into ExecutionPlan
  3. Build dependency graph (topological sort)
  4. Execute tasks level-by-level (tasks with no pending deps run in parallel via asyncio.gather)
  5. Pass sub-agent results downstream via params injection
  6. Return merged output dict + agent_trace list

### 2.2 Anomaly Agent (anomaly_agent.py)

Detection algorithm:
  1. Query: SELECT DATE(time), lat_bin, lon_bin, AVG(temp) FROM marine_data
             WHERE pres < 10 AND time > NOW() - INTERVAL '35 days'
             GROUP BY 1, lat_bin, lon_bin
     (lat_bin = ROUND(latitude::numeric, 0), lon_bin = ROUND(longitude::numeric, 0))
  2. For each grid cell: compute rolling 30-day mean + std dev
  3. Marine Heatwave: current temp > mean + 2*std AND this condition holds 5+ consecutive days
  4. Hypoxia: AVG(doxy) < 60 umol/kg where doxy is not null
  5. INSERT alert into anomaly_alerts ON CONFLICT (alert_type, ocean_basin, detected_at::date) DO UPDATE
  6. Sleep 6 hours, repeat

Alert severity mapping:
  MHW anomaly > 4°C  -> CRITICAL
  MHW anomaly > 2°C  -> HIGH
  MHW anomaly > 1°C  -> MODERATE
  MHW anomaly > 0°C  -> LOW (precursor)

---

## 3. Data Schema (Darwin Core — marine_biodiversity)

VARUNA follows the Darwin Core biodiversity data standard (https://dwc.tdwg.org/) for the marine_biodiversity table.
This ensures direct compatibility with CMLRE's actual data format when real CMLRE data becomes available.

Key fields mapped to Darwin Core terms:
  occurrence_id      -> dwc:occurrenceID
  scientific_name    -> dwc:scientificName
  taxon_rank         -> dwc:taxonRank
  decimal_latitude   -> dwc:decimalLatitude
  decimal_longitude  -> dwc:decimalLongitude
  event_date         -> dwc:eventDate
  depth_m            -> dwc:minimumDepthInMeters
  individual_count   -> dwc:individualCount
  recorded_by        -> dwc:recordedBy

Cross-domain join logic (used in /api/v1/correlate):
  SELECT b.scientific_name, b.event_date, b.decimal_latitude, b.decimal_longitude,
         m.temp, m.psal, m.doxy, m.chla, m.platform_number
  FROM marine_biodiversity b
  JOIN LATERAL (
    SELECT * FROM marine_data m
    WHERE ST_DWithin(m.geom, b.geom, 50000)   -- 50km radius
      AND m.time BETWEEN b.event_date - INTERVAL '7 days'
                     AND b.event_date + INTERVAL '7 days'
      AND m.pres < 20   -- surface layer
    ORDER BY m.geom <-> b.geom
    LIMIT 3
  ) m ON true
  WHERE b.scientific_name = 

---

## 4. API Reference

POST /api/v1/chat
  Body: { question: str, session: str, force_sql: bool }
  Response: ChatOut (single-shot chain)

POST /api/v1/agent/chat    [NEW]
  Body: { question: str, session: str }
  Response: ChatOut + { agent_trace: AgentStep[] }

GET /api/v1/anomalies      [NEW]
  Params: basin (str), severity (str), limit (int, default 20)
  Response: { alerts: AnomalyAlert[] }

GET /api/v1/biodiversity   [NEW]
  Params: basin (str), species (str), limit (int, default 500)
  Response: { occurrences: SpeciesOccurrence[] }

GET /api/v1/correlate      [NEW]
  Params: species (str), days (int, default 90)
  Response: { correlations: CrossDomainRow[] }

GET /api/v1/floats
GET /api/v1/trajectory/{platform_number}
GET /api/v1/profile/{platform_number}
GET /api/v1/stats
GET /api/v1/debug/{trace_id}
GET /api/v1/export

---

## 5. Zero-Docker Native Infrastructure

### Native Production Services
- **PostgreSQL 16 with PostGIS 3.4**: Local database cluster (`port 5432`) managing `public.marine_data`, `public.marine_biodiversity`, and `public.anomaly_alerts`.
- **Qdrant Vector Database**: Native binary (`port 6333`) or Qdrant Cloud cluster managing 3 semantic namespaces (`argo_knowledge`, `argo_schema`, `bio_knowledge`).
- **Redis 7.2**: In-memory caching & session sliding-window store (`port 6379`), with in-process dictionary fallback.
- **OpenRouter HTTPS API**: Cloud LLM inference endpoint routing all generation to `nvidia/nemotron-ultra-550b-a55b:free` (Zero local model baggage).

---

## 6. Comprehensive Architecture Specification Series
- [01_SYSTEM_OVERVIEW.md](file:///e:/Hackathons/floatchatai-main/docs/architecture/01_SYSTEM_OVERVIEW.md) — Master architecture and subsystems
- [02_MULTI_AGENT_ORCHESTRATION.md](file:///e:/Hackathons/floatchatai-main/docs/architecture/02_MULTI_AGENT_ORCHESTRATION.md) — Task DAG execution engine
- [03_NETCDF_INGESTION_AND_HPC_ETL.md](file:///e:/Hackathons/floatchatai-main/docs/architecture/03_NETCDF_INGESTION_AND_HPC_ETL.md) — NetCDF V3.1 parsing specs
- [04_CMLRE_BIODIVERSITY_FUSION.md](file:///e:/Hackathons/floatchatai-main/docs/architecture/04_CMLRE_BIODIVERSITY_FUSION.md) — Darwin Core cross-domain joins
- [05_PROACTIVE_ANOMALY_ENGINE.md](file:///e:/Hackathons/floatchatai-main/docs/architecture/05_PROACTIVE_ANOMALY_ENGINE.md) — Hobday MHW and Hypoxia formulas
- [06_DATABASE_AND_VECTOR_SCHEMA.md](file:///e:/Hackathons/floatchatai-main/docs/architecture/06_DATABASE_AND_VECTOR_SCHEMA.md) — PostgreSQL + Qdrant DDLs
- [07_LLM_OPENROUTER_ENGINE.md](file:///e:/Hackathons/floatchatai-main/docs/architecture/07_LLM_OPENROUTER_ENGINE.md) — OpenRouter Nemotron integration
- [08_FRONTEND_OPERATIONS_CENTER.md](file:///e:/Hackathons/floatchatai-main/docs/architecture/08_FRONTEND_OPERATIONS_CENTER.md) — Command center HUD design
- [CELLULAR_TECHNICAL_CHECKLIST.md](file:///e:/Hackathons/floatchatai-main/docs/architecture/CELLULAR_TECHNICAL_CHECKLIST.md) — Cellular codebase audit

---

## 6. Competitor Analysis — Why We Beat OceanIQ

OceanIQ (Prior SIH Reference Benchmark) — public repo: github.com/PaarthNo1/OceanIQ--AI-Intelligent

What OceanIQ did well:
  - Real-time IFREMER/Argo ingestion with automatic DAC detection
  - PostgreSQL + PostGIS
  - Dual FAISS indices (profile semantics + schema-linking)
  - Gemini-based SQL generation with validator/sanitizer/executor chain
  - JWT auth, rate limiting

OceanIQ limitations (our literature gap, per VARUNA Master Guide Section 4):
  1. Single-shot pipeline — no multi-step agentic planning for compound questions
  2. Stateless — no multi-turn session memory
  3. Purely reactive — never proactively surfaces anomalies
  4. Single dataset (ARGO only) — no biodiversity/taxonomy fusion
  5. No frontend/visualization in public repo
  6. No offline/low-bandwidth mode (requested by original PS text)

VARUNA closes all 6 gaps:
  1. Multi-Agent Task DAG Planner
  2. Redis-backed multi-turn session memory
  3. Proactive Anomaly and Early-Warning Agent
  4. Cross-domain INCOIS + CMLRE biodiversity fusion
  5. Full production frontend with ocean-themed command center UI
  6. Rule-based SQL fallback for offline/degraded mode
