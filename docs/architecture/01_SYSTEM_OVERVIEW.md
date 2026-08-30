# VARUNA Technical Architecture — 01. System Overview

> **System Designation**: VARUNA (Vedic Deity of Oceans and Cosmic Waters)  
> **Classification**: Agentic AI Ocean & Marine Ecosystem Intelligence Platform  
> **Mandate**: National Marine Data Backbone fusing INCOIS Physical Argo Observations + CMLRE Marine Living Resources  
> **Target Audience**: INCOIS Oceanographers, CMLRE Marine Biologists, State Disaster Management Authorities (SDMAs), Coastal Fisheries Departments  

---

## 1. High-Level System Architecture

VARUNA is architected as an event-driven, multi-agent cognitive mesh that unifies physical oceanographic observations with biological ecosystem data.

```mermaid
graph TB
    subgraph Ingestion_Layer [1. High-Performance Ingestion & ETL Layer]
        INCOIS_FTP[INCOIS / IFREMER GDAC FTP] -->|NetCDF-4 Binaries| NetCDF_Parser[NetCDF Vectorized Parser netcdf4 + pyarrow]
        OBIS_API[OBIS / GBIF APIs] -->|Darwin Core JSON| Bio_Ingest[Darwin Core Standardized Ingest]
        
        NetCDF_Parser --> Parquet_Store[(Parquet Columnar Archive data/processed/)]
        NetCDF_Parser --> PostGIS_Copy[(PostgreSQL + PostGIS marine_data)]
        Bio_Ingest --> PostGIS_Bio[(PostgreSQL marine_biodiversity)]
        
        NetCDF_Parser -.->|Profile Summaries| Qdrant_Argo[(Qdrant: argo_knowledge)]
        Bio_Ingest -.->|Species Ecology| Qdrant_Bio[(Qdrant: bio_knowledge)]
    end

    subgraph Autonomous_Proactive_Layer [2. Autonomous Early-Warning & Anomaly Engine]
        PostGIS_Copy --> Anomaly_Agent[Proactive Anomaly Scanner 6-Hour Cron]
        Anomaly_Agent --> MHW_Calc[Hobday 2016 MHW Climatology Engine]
        Anomaly_Agent --> Hypoxia_Calc[Hypoxia / OMZ Detector doxy < 60]
        MHW_Calc --> Anomaly_DB[(public.anomaly_alerts)]
        Hypoxia_Calc --> Anomaly_DB
        Anomaly_DB --> Alert_Feed[Live Anomaly Feed API /api/v1/anomalies]
    end

    subgraph Cognitive_Agentic_Layer [3. Multi-Agent Task DAG Cognitive Mesh]
        User_NL[User Natural Language Query] --> API_Gateway[FastAPI Gateway /api/v1/agent/chat]
        API_Gateway --> Planner_Agent[Planner / Orchestrator Agent Nemotron-Ultra 550B]
        
        Planner_Agent --> Task_DAG{Dynamic Task DAG}
        
        Task_DAG -->|NL->SQL Task| SQL_Agent[SQL-Gen Sub-Agent + Schema RAG]
        Task_DAG -->|Semantic Task| Vector_Agent[Hybrid Retrieval Sub-Agent BM25 + Qdrant]
        Task_DAG -->|Cross-Domain Task| Bio_Agent[Biodiversity Entity Resolution Sub-Agent]
        Task_DAG -->|Comparison Task| Comp_Agent[Multi-Region Aggregator Sub-Agent]
        
        SQL_Agent --> PostGIS_Copy
        Vector_Agent --> Qdrant_Argo
        Bio_Agent --> PostGIS_Bio
        Bio_Agent --> PostGIS_Copy
        
        SQL_Agent --> Synthesizer[Synthesizer Agent Nemotron-Ultra 550B]
        Vector_Agent --> Synthesizer
        Bio_Agent --> Synthesizer
        Comp_Agent --> Synthesizer
        
        Synthesizer --> Trace_Engine[Zero-Hallucination Provenance Tracer]
    end

    subgraph Presentation_Layer [4. Naval Operations Center UI - Next.js 14]
        Trace_Engine --> NextJS_Frontend[Command Center Frontend]
        Alert_Feed --> NextJS_Frontend
        
        NextJS_Frontend --> Ocean_Copilot[Ocean Copilot with Live Agent Graph]
        NextJS_Frontend --> Situational_Map[Deck.gl + Mapbox Dual-Layer Canvas]
        NextJS_Frontend --> Cross_Domain[INCOIS x CMLRE Explorer]
        NextJS_Frontend --> Plotly_Suite[15+ Oceanographic Plotly Charts]
        NextJS_Frontend --> Globe_3D[Three.js Bioluminescent Globe]
    end
```

---

## 2. Subsystem Descriptions

### Subsystem 1: Dual-Domain Ingestion & Storage Architecture
- **Physical Ocean Stream**: Ingests multi-parameter NetCDF files from INCOIS Argo Float array (temperature, salinity, pressure, dissolved oxygen, chlorophyll-a, nitrate, pH, backscatter).
- **Marine Living Resources Stream**: Normalized using the international Darwin Core standard (`dwc:scientificName`, `dwc:decimalLatitude`, `dwc:decimalLongitude`, `dwc:eventDate`, `dwc:individualCount`).
- **Hybrid Storage Model**:
  - **Relational / Geospatial**: PostgreSQL with PostGIS extension for microsecond spatial filtering (`ST_DWithin`, bounding box indexing).
  - **Columnar Analytics**: Parquet files read via DuckDB for multi-year aggregation queries.
  - **Vector Indices**: Qdrant vector database managing 3 dedicated semantic namespaces.

### Subsystem 2: Proactive Marine Anomaly & Early-Warning Engine
Unlike traditional reactive dashboards, VARUNA runs continuous background statistical scans over physical ocean measurements:
- Identifies **Marine Heatwave (MHW)** precursors using climatological baseline exceedance ($\ge 90\text{th}$ percentile for 5+ days).
- Detects **Oxygen Minimum Zone (OMZ)** expansions ($DOXY < 60\,\mu\text{mol/kg}$) threatening demersal fisheries.
- Automatically maps impacted biological species habitats by intersecting anomaly bounding boxes with Darwin Core occurrence records.

### Subsystem 3: Multi-Agent Task DAG Cognitive Mesh
Replaces single-shot RAG (OceanIQ) with an asynchronous Directed Acyclic Graph (DAG) executor:
- **Planner Agent**: Parses user intent and produces an optimized execution graph.
- **Specialized Sub-Agents**: Dispatched in parallel with topological dependency resolution.
- **Synthesizer Agent**: Merges tabular, spatial, and semantic outputs into scientific prose with verified numeric citations.

### Subsystem 4: Command Center Frontend
A zero-compromise, military/scientific command center UI built in Next.js 14:
- Hardware-accelerated Deck.gl layers rendering 3,800+ active ARGO floats and biodiversity observations.
- Live `AgentGraph` visualization rendering real-time sub-agent execution status and latencies.
- 15+ specialized Plotly chart types including Hovmöller diagrams, T-S curves with UNESCO isopycnals, and 3D bathymetric profiles.
