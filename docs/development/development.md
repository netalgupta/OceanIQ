# VARUNA — Development Rules & Zero-Docker Local Setup

> **Development Guide Index**: Unified local workflow, zero-Docker environment configuration, coding invariants, and Git conventions.

---

## 1. Native Local Setup (Zero Docker)

### Prerequisites
- **Python 3.11+**
- **Node.js 20+**
- **PostgreSQL 15+ with PostGIS Extension** (Local PostgreSQL or Supabase / Cloud Postgres)
- **Qdrant Vector Database** (Standalone binary / native service or Qdrant Cloud)
- **Git**

### Step-by-Step

1. **Clone the repository & initialize environment**:
   ```bash
   cd e:\Hackathons\floatchatai-main
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # Windows PowerShell (or source venv/bin/activate on Linux/macOS)
   pip install -r requirements.txt
   ```

3. **Configure `backend/.env`**:
   Copy `.env.example` to `backend/.env`:
   ```env
   FLOATCHAT_APP_ENV=dev
   PG_DSN=postgresql://postgres:postgres@localhost:5432/argo_data
   QDRANT_URL=http://localhost:6333
   REDIS_URL=redis://localhost:6379/0
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   OPENROUTER_MODEL=nvidia/nemotron-ultra-550b-a55b:free
   OPENROUTER_EMBED_MODEL=nomic-ai/nomic-embed-text-v1.5:free
   ```

4. **Seed Initial Marine Biodiversity Data**:
   ```bash
   python -m src.ingestion.seed_biodiversity
   ```

5. **Start FastAPI Backend Server**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   Interactive Swagger API docs available at: `http://localhost:8000/docs`

6. **Frontend Setup (Terminal 2)**:
   ```bash
   cd frontend
   npm install
   # Configure frontend/.env.local with NEXT_PUBLIC_API_URL=http://localhost:8000
   npm run dev
   ```
   Command Center UI available at: `http://localhost:3000`

---

## 2. Inviolable Backend Development Rules

- **Zero-Local-LLM Invariant**: No `ollama_client.py` in the primary generation path — all cognitive requests route to OpenRouter (`nvidia/nemotron-ultra-550b-a55b:free`).
- **No Blocking Imports**: Never import heavy neural libraries (e.g. `SentenceTransformer`) at server startup.
- **Strict SQL Sanitization**: All queries passed to `run_sql()` must pass through `extract_sql()` + `sanitize_sql()` guaranteeing `SELECT`-only semantics.
- **Zero Secrets in Git**: Never commit `.env` or `.env.local` files.
- **Async Non-Blocking I/O**: All FastAPI route handlers, database operations, and external API requests must be `async/await`.

---

## 3. Team Workstream & Git Strategy

### Branch Strategy
- `main` — Production-ready, always buildable (`npm run build` must pass).
- `dev/M1-aryan` — Aryan's feature branches (Orchestrator, RAG, Anomaly Agent, Synthesizer, API Gateway).
- `dev/M2-aditya` — Aditya's feature branches (Ingestion, Darwin Core Seeding, PostGIS Schema).
- `dev/M3-sahil` — Sahil's feature branches (Predictive MHW ConvLSTM, 1D-CNN Sensor QC Autoencoder).
- `dev/M4-advay` — Advay's feature branches (App Shell, ChatPanel, AgentGraph DAG, 3D Globe).
- `dev/M5-netal` — Netal's feature branches (OceanMap, Trajectories, AnomalyAlerts).
- `dev/M6-kanishka` — Kanishka's feature branches (CrossDomainExplorer, 15+ Plotly Charts, SIH Deck & Video).

---

## 4. Comprehensive Development Guides
- [01_LOCAL_SETUP_NO_DOCKER.md](file:///e:/Hackathons/floatchatai-main/docs/development/01_LOCAL_SETUP_NO_DOCKER.md) — Detailed zero-docker setup guide
- [02_CODING_STANDARDS_AND_RULES.md](file:///e:/Hackathons/floatchatai-main/docs/development/02_CODING_STANDARDS_AND_RULES.md) — 10 architectural invariants
- [03_NETCDF_WORKFLOW_GUIDE.md](file:///e:/Hackathons/floatchatai-main/docs/development/03_NETCDF_WORKFLOW_GUIDE.md) — Real ARGO NetCDF download and ETL guide
- [04_API_CONTRACTS.md](file:///e:/Hackathons/floatchatai-main/docs/development/04_API_CONTRACTS.md) — Complete REST & WebSocket API contracts
