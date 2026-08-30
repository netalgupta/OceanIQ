-- ================================================================
-- FloatChat AI — Production Schema (PostgreSQL 16 + PostGIS 3.4)
-- ================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ── Float registry ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.floats (
    wmo_id          VARCHAR(20)  PRIMARY KEY,
    platform_type   VARCHAR(50),                   -- 'Argo', 'BGC-Argo', 'Deep-Argo'
    deployment_date TIMESTAMPTZ,
    program         VARCHAR(100),
    country         VARCHAR(60),
    institution     VARCHAR(100),
    last_seen       TIMESTAMPTZ,
    last_lat        DOUBLE PRECISION,
    last_lon        DOUBLE PRECISION,
    geom            GEOGRAPHY(POINT, 4326),        -- PostGIS spatial index
    total_profiles  INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_floats_geom ON public.floats USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_floats_last_seen ON public.floats(last_seen DESC);

-- ── Main measurements table (year-partitioned) ──────────────────
CREATE TABLE IF NOT EXISTS public.marine_data (
    id              BIGSERIAL,
    platform_number INT4            NOT NULL,
    cycle_number    INT4,
    data_mode       CHAR(1),                       -- R=realtime D=delayed A=adjusted
    time            TIMESTAMPTZ     NOT NULL,
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    geom            GEOGRAPHY(POINT, 4326),        -- auto-computed from lat/lon
    pres            DOUBLE PRECISION,              -- pressure dbar ≈ depth m
    pres_qc         SMALLINT DEFAULT 0,
    temp            DOUBLE PRECISION,              -- sea temperature °C
    temp_qc         SMALLINT DEFAULT 0,
    psal            DOUBLE PRECISION,              -- practical salinity PSU
    psal_qc         SMALLINT DEFAULT 0,
    doxy            DOUBLE PRECISION,              -- dissolved oxygen µmol/kg
    doxy_qc         SMALLINT DEFAULT 0,
    chla            DOUBLE PRECISION,              -- chlorophyll-a mg/m³
    chla_qc         SMALLINT DEFAULT 0,
    nitrate         DOUBLE PRECISION,              -- nitrate µmol/kg
    nitrate_qc      SMALLINT DEFAULT 0,
    ph_in_situ_total DOUBLE PRECISION,             -- pH
    ph_qc           SMALLINT DEFAULT 0,
    bbp700          DOUBLE PRECISION,              -- particulate backscattering
    irradiance      DOUBLE PRECISION,              -- downwelling irradiance
    PRIMARY KEY (id, time)
) PARTITION BY RANGE (time);

-- Year partitions 2018–2026
CREATE TABLE IF NOT EXISTS public.marine_data_2018 PARTITION OF public.marine_data
    FOR VALUES FROM ('2018-01-01') TO ('2019-01-01');
CREATE TABLE IF NOT EXISTS public.marine_data_2019 PARTITION OF public.marine_data
    FOR VALUES FROM ('2019-01-01') TO ('2020-01-01');
CREATE TABLE IF NOT EXISTS public.marine_data_2020 PARTITION OF public.marine_data
    FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');
CREATE TABLE IF NOT EXISTS public.marine_data_2021 PARTITION OF public.marine_data
    FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');
CREATE TABLE IF NOT EXISTS public.marine_data_2022 PARTITION OF public.marine_data
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
CREATE TABLE IF NOT EXISTS public.marine_data_2023 PARTITION OF public.marine_data
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE IF NOT EXISTS public.marine_data_2024 PARTITION OF public.marine_data
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE IF NOT EXISTS public.marine_data_2025 PARTITION OF public.marine_data
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE IF NOT EXISTS public.marine_data_2026 PARTITION OF public.marine_data
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

-- Spatial + time indexes on each partition
DO $$ BEGIN
  EXECUTE 'CREATE INDEX IF NOT EXISTS md_2025_spatial ON public.marine_data_2025 USING GIST(geom)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS md_2025_time    ON public.marine_data_2025(time DESC)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS md_2025_plat    ON public.marine_data_2025(platform_number, time)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS md_2024_spatial ON public.marine_data_2024 USING GIST(geom)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS md_2024_time    ON public.marine_data_2024(time DESC)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS md_2024_plat    ON public.marine_data_2024(platform_number, time)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS md_2023_spatial ON public.marine_data_2023 USING GIST(geom)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS md_2023_time    ON public.marine_data_2023(time DESC)';
  EXECUTE 'CREATE INDEX IF NOT EXISTS md_2023_plat    ON public.marine_data_2023(platform_number, time)';
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- ── Conversation memory (persistent) ───────────────────────────
CREATE TABLE IF NOT EXISTS public.sessions (
    session_id  VARCHAR(64) PRIMARY KEY,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    messages    JSONB DEFAULT '[]'::JSONB,
    user_prefs  JSONB DEFAULT '{}'::JSONB
);

-- ── Query feedback ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.query_feedback (
    id              BIGSERIAL PRIMARY KEY,
    session_id      VARCHAR(64),
    query           TEXT NOT NULL,
    sql_generated   TEXT,
    answer          TEXT,
    rating          SMALLINT CHECK (rating BETWEEN 1 AND 5),
    correction      TEXT,
    pipeline_trace  JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Knowledge graph edges ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.kg_edges (
    id          BIGSERIAL PRIMARY KEY,
    src_type    VARCHAR(40),
    src_id      VARCHAR(100),
    rel         VARCHAR(60),
    dst_type    VARCHAR(40),
    dst_id      VARCHAR(100),
    weight      DOUBLE PRECISION DEFAULT 1.0,
    meta        JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_kg_src ON public.kg_edges(src_type, src_id);
CREATE INDEX IF NOT EXISTS idx_kg_dst ON public.kg_edges(dst_type, dst_id);

-- ── Ingestion log ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.ingestion_log (
    id              BIGSERIAL PRIMARY KEY,
    source_file     VARCHAR(500),
    status          VARCHAR(20) DEFAULT 'pending',
    rows_inserted   INT DEFAULT 0,
    error_msg       TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);
