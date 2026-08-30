# VARUNA Development Guide — 01. Local Setup (Zero-Docker Native Stack)

> **Philosophy**: Zero Docker baggage. Fast, lightweight native local development using Python virtual environments, local/cloud PostgreSQL with PostGIS, and Node.js Next.js dev server.

---

## 1. Prerequisites

1. **Python 3.11+** (Verify with `python --version`)
2. **Node.js 20+** (Verify with `node -v`)
3. **PostgreSQL 15+ with PostGIS Extension** (Local PostgreSQL installation or Supabase / Neon / Cloud Postgres instance)
4. **Qdrant Vector Database** (Standalone binary `qdrant.exe` / native service or Qdrant Cloud cluster)
5. **OpenRouter API Key** (With access to `nvidia/nemotron-ultra-550b-a55b:free`)

---

## 2. Step-by-Step Setup Guide

### Step 1: PostgreSQL + PostGIS Initialization
Connect to your local or cloud PostgreSQL instance with `psql` or pgAdmin and run:

```sql
CREATE DATABASE argo_data;
\c argo_data;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

---

### Step 2: Backend Setup (Python 3.11)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Configure `.env` file in `backend/.env`:
```env
FLOATCHAT_APP_ENV=dev
FLOATCHAT_LOG_LEVEL=DEBUG
FLOATCHAT_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# PostgreSQL DSN (Replace with your local or cloud credentials)
PG_DSN=postgresql://postgres:postgres@localhost:5432/argo_data

# Qdrant Vector DB (Local standalone binary or Cloud)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=argo_knowledge

# Redis Session Memory (Optional, falls back to in-memory dictionary if offline)
REDIS_URL=redis://localhost:6379/0

# OpenRouter Nemotron-550B LLM (Zero Local LLM Baggage)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=nvidia/nemotron-ultra-550b-a55b:free
OPENROUTER_EMBED_MODEL=nomic-ai/nomic-embed-text-v1.5:free
```

---

### Step 3: Seed Initial Ocean & Biodiversity Data

Run the Darwin Core biodiversity seeding script to populate 500+ Indian Ocean marine species records:

```bash
# Inside backend/ with venv activated:
python -m src.ingestion.seed_biodiversity
```

Run the database check to verify all tables and PostGIS spatial indexes:
```bash
python check_db.py
```

---

### Step 4: Launch FastAPI Backend Server

```bash
# Start uvicorn development server on port 8000
uvicorn main:app --reload --port 8000
```
- API Swagger Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

---

### Step 5: Frontend Setup (Next.js 14)

Open a second terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Configure local environment in frontend/.env.local
```

#### Configure `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1IjoiYXJ5YW5sb210ZSIsImEiOiJjbHgwZnp2eTQwMGtqMmpxc2V4Ynp4N3hyIn0.example
```

#### Launch Next.js Dev Server:
```bash
npm run dev
```
Open your browser at **`http://localhost:3000`** to access the VARUNA Command Center UI!
