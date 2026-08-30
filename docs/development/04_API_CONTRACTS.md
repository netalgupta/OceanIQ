# VARUNA Development Guide — 04. API Contracts & Endpoint Specifications

---

## 1. REST Endpoints Overview

| Method | Route | Description | Primary Consumer |
|---|---|---|---|
| `POST` | `/api/v1/agent/chat` | Main multi-agent DAG prompt execution | `ChatPanel.tsx` (Agent mode) |
| `POST` | `/api/v1/chat` | Single-shot fallback Q&A endpoint | `ChatPanel.tsx` (Quick mode) |
| `GET` | `/api/v1/anomalies` | Live Marine Heatwave & hypoxia alerts feed | `AnomalyAlerts.tsx` |
| `GET` | `/api/v1/biodiversity` | CMLRE species occurrence records | `OceanMap.tsx` |
| `GET` | `/api/v1/correlate` | Species ↔ Physical ocean spatial correlation | `CrossDomainExplorer.tsx` |
| `GET` | `/api/v1/floats` | Active ARGO fleet list | `OceanMap.tsx`, `Explorer` |
| `GET` | `/api/v1/trajectory/{id}` | Float historical drift track | `TrajectoryLayer.tsx` |
| `GET` | `/api/v1/profile/{id}` | Vertical depth profile measurements | `DepthProfile.tsx` |
| `GET` | `/api/v1/export` | CSV / Parquet tabular data export | Dataset Browser |
| `POST` | `/api/v1/ml/forecast-mhw` | 7-Day spatio-temporal MHW forecast surface | `AnomalyAlerts.tsx` |
| `POST` | `/api/v1/ml/qc-detect` | 1D-CNN deep sensor drift & biofouling detection | Ingestion / QC Monitor |
| `GET` | `/health` | Server and database health check | Monitoring |

---

## 2. Request & Response Payload Contracts

### 2.1 Multi-Agent Prompt Execution (`POST /api/v1/agent/chat`)

#### Request Body:
```json
{
  "question": "Compare dissolved oxygen and temperature in the Arabian Sea last 6 months against the equator and show affected marine species.",
  "session_id": "user_session_4921",
  "user_lat": 18.9,
  "user_lon": 72.8
}
```

#### Response Body (`200 OK`):
```json
{
  "ok": true,
  "answer_markdown": "### 🌊 Marine Ecosystem Assessment\n\nOver the past 6 months in the **Arabian Sea** (5°N–25°N, 45°E–77°E), sea surface temperatures averaged **29.14°C**, representing an anomaly of **+1.8°C** above the baseline. Dissolved oxygen in the upper 50m averaged **48.2 µmol/kg**, indicating an expansion of the Oxygen Minimum Zone (OMZ).\n\nIn contrast, the **Equatorial Indian Ocean** maintained normoxic conditions with average DOXY of **82.4 µmol/kg** and SST of **28.2°C**.\n\n### 🐟 Biological Species Impact\n* **Sardinella longiceps (Indian Oil Sardine)**: Correlated float data from WMO 1902303 indicates habitat compression as surface temperatures exceeded their thermal optimum (22–26°C).\n\n<details>\n<summary>SQL Queries Executed</summary>\n\n```sql\nSELECT DATE_TRUNC('month', time) AS month, AVG(temp) AS avg_temp, AVG(doxy) AS avg_doxy FROM public.marine_data WHERE latitude BETWEEN 5 AND 25 AND longitude BETWEEN 45 AND 77 GROUP BY 1 ORDER BY 1;\n```\n</details>",
  "sql": "SELECT DATE_TRUNC('month', time) AS month...",
  "rows": [
    {"month": "2026-03-01", "avg_temp": 29.14, "avg_doxy": 48.2}
  ],
  "agent_trace": {
    "plan_id": "plan_9f82b1c4",
    "total_latency_ms": 1420.5,
    "tasks": [
      {"task_id": "t1", "agent": "SQL_GEN", "status": "COMPLETED", "duration_ms": 420.2},
      {"task_id": "t2", "agent": "BIODIVERSITY", "status": "COMPLETED", "duration_ms": 180.4},
      {"task_id": "t3", "agent": "SYNTHESIZER", "status": "COMPLETED", "duration_ms": 540.1}
    ]
  },
  "viz_specs": {
    "chart_type": "time_series",
    "x": ["2026-01-01", "2026-02-01", "2026-03-01"],
    "y": [28.4, 28.9, 29.14]
  }
}
```

---

### 2.2 Proactive Anomaly Alerts (`GET /api/v1/anomalies`)

#### Response Body (`200 OK`):
```json
{
  "alerts": [
    {
      "id": 101,
      "alert_type": "MARINE_HEATWAVE",
      "severity": "CRITICAL",
      "ocean_basin": "arabian_sea",
      "lat_min": 14.0,
      "lat_max": 22.0,
      "lon_min": 62.0,
      "lon_max": 74.0,
      "metric_value": 3.4,
      "baseline_value": 28.1,
      "detected_at": "2026-08-14T18:00:00Z",
      "active": true,
      "affected_species": [
        {
          "scientific_name": "Sardinella longiceps",
          "common_name": "Indian Oil Sardine",
          "vulnerability_note": "Thermal threshold exceeded; stock retreat to deeper waters"
        }
      ],
      "policy_advisory": "Advisory issued for Malabar coast artisanal fisheries regarding altered schooling patterns."
    }
  ]
}
```
