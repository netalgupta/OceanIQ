# VARUNA Technical Architecture — 06. Database & Vector Schema

> **Storage Topology**: PostgreSQL with PostGIS extension (relational/spatial), Qdrant Vector Engine (3 semantic namespaces), DuckDB (columnar Parquet analytics), and Redis (session memory).

---

## 1. Relational & Geospatial Schema (PostgreSQL + PostGIS)

```mermaid
erDiagram
    FLOATS ||--o{ MARINE_DATA : records
    MARINE_BIODIVERSITY ||--o{ ANOMALY_ALERTS : impacts
    QUERY_FEEDBACK }o--|| SESSIONS : rates
    
    FLOATS {
        varchar wmo_id PK
        varchar platform_type
        varchar program
        timestamp last_seen
        double last_lat
        double last_lon
        geography geom
        int total_profiles
        varchar country
    }

    MARINE_DATA {
        bigserial id PK
        int4 platform_number FK
        timestamptz time PK
        double latitude
        double longitude
        geography geom
        double pres
        double temp
        double psal
        double doxy
        double chla
        double nitrate
        double ph_in_situ_total
        double bbp700
    }

    MARINE_BIODIVERSITY {
        bigserial id PK
        varchar occurrence_id UK
        varchar scientific_name
        varchar common_name
        varchar taxon_rank
        double decimal_latitude
        double decimal_longitude
        geography geom
        date event_date
        double depth_m
        varchar ocean_basin
        int4 individual_count
    }

    ANOMALY_ALERTS {
        bigserial id PK
        varchar alert_type
        varchar severity
        varchar ocean_basin
        double lat_min
        double lat_max
        double lon_min
        double lon_max
        double metric_value
        double baseline_value
        timestamptz detected_at
        boolean active
        jsonb affected_species
        text policy_advisory
    }
```

---

## 2. Table DDLs & Indexing Strategies

### 2.1 Partitioned Physical Ocean Measurements (`public.marine_data`)
```sql
CREATE TABLE IF NOT EXISTS public.marine_data (
    id               BIGSERIAL,
    platform_number  INT4 NOT NULL,
    time             TIMESTAMPTZ NOT NULL,
    latitude         DOUBLE PRECISION NOT NULL,
    longitude        DOUBLE PRECISION NOT NULL,
    geom             GEOGRAPHY(POINT, 4326),
    pres             DOUBLE PRECISION,
    pres_qc          SMALLINT DEFAULT 1,
    temp             DOUBLE PRECISION,
    temp_qc          SMALLINT DEFAULT 1,
    psal             DOUBLE PRECISION,
    psal_qc          SMALLINT DEFAULT 1,
    doxy             DOUBLE PRECISION,
    doxy_qc          SMALLINT DEFAULT 1,
    chla             DOUBLE PRECISION,
    nitrate          DOUBLE PRECISION,
    ph_in_situ_total DOUBLE PRECISION,
    bbp700           DOUBLE PRECISION,
    cycle_number     INT4,
    data_mode        CHAR(1) DEFAULT 'R',
    PRIMARY KEY (id, time)
) PARTITION BY RANGE (time);

-- Year Partitions (2020 through 2026)
CREATE TABLE IF NOT EXISTS marine_data_2024 PARTITION OF public.marine_data
    FOR VALUES FROM ('2024-01-01 00:00:00+00') TO ('2025-01-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS marine_data_2025 PARTITION OF public.marine_data
    FOR VALUES FROM ('2025-01-01 00:00:00+00') TO ('2026-01-01 00:00:00+00');
CREATE TABLE IF NOT EXISTS marine_data_2026 PARTITION OF public.marine_data
    FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');

-- Indexes
CREATE INDEX IF NOT EXISTS idx_marine_geom ON public.marine_data USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_marine_time_platform ON public.marine_data (platform_number, time DESC);
CREATE INDEX IF NOT EXISTS idx_marine_pres ON public.marine_data (pres);
```

---

## 3. Vector Database Architecture (Qdrant 3-Collection Topology)

| Collection | Vector Dimension | Distance Metric | Content & Schema |
|---|---|---|---|
| `argo_knowledge` | 768-dim / 1536-dim | Cosine | Natural-language profile summary texts (WMO ID, date, location, surface temp, mixed layer depth, thermocline gradient) |
| `argo_schema` | 768-dim / 1536-dim | Cosine | PostgreSQL table schemas, column descriptions, and 50+ curated NL→SQL few-shot examples |
| `bio_knowledge` | 768-dim / 1536-dim | Cosine | Species habitat descriptions, ecological niches, thermal tolerances, and CMLRE taxonomy literature |

---

## 4. Redis Multi-Turn Conversation & Working Memory

```mermaid
graph LR
    UserTurn[User Prompt: Session XYZ] --> RedisLookup{Redis Session Key: session:XYZ:history}
    RedisLookup -->|Hit| LoadHistory[Load Last 10 Turns JSON]
    RedisLookup -->|Miss| FallbackInMemory[Fallback to In-Process Dict]
    
    LoadHistory --> SlidingWindow[Sliding Window Context Assembly]
    SlidingWindow --> PromptContext[Injected into Planner / SQL Agent]
```
