# VARUNA Development Guide — 03. NetCDF Ingestion Workflow

> **Guide Purpose**: How to download real Indian Ocean ARGO NetCDF files from IFREMER/INCOIS GDAC servers and ingest them into PostgreSQL and Parquet.

---

## 1. Downloading Real ARGO Float NetCDF Files

### 1.1 From IFREMER / Coriolis GDAC Server
You can download public Indian Ocean ARGO NetCDF files directly from the IFREMER GDAC mirror via HTTPS or FTP:

- **Web Browser Interface**: `https://data-argo.ifremer.fr/geo/indian_ocean/`
- **FTP Access**: `ftp://ftp.ifremer.fr/ifremer/argo/geo/indian_ocean/`

#### Recommended Floats to Download:
- `1902303` (BGC float, active in Eastern Arabian Sea)
- `5906478` (Core Argo float, Northern Arabian Sea)
- `2903567` (Deep Argo float, Bay of Bengal)
- `4901234` (Equatorial Indian Ocean)

Place the downloaded `.nc` or `.nc4` files into the raw directory:
```
backend/data/raw/
  ├── 1902303_prof.nc
  ├── 5906478_prof.nc
  └── 2903567_prof.nc
```

---

## 2. Executing the Batch Ingestion Pipeline

With your virtual environment activated, run:

```bash
# Ingest single NetCDF file
python -c "import asyncio; from src.ingestion.pipeline import ingest_file; asyncio.run(ingest_file('./data/raw/1902303_prof.nc'))"

# Ingest entire directory of NetCDF files in batch
python -c "import asyncio; from src.ingestion.pipeline import run_batch; asyncio.run(run_batch('./data/raw'))"
```

The pipeline will:
1. Parse the NetCDF dataset using `netcdf_reader.py`.
2. Extract all profiles, cycle numbers, temperatures, salinities, and BGC parameters.
3. Save an immutable columnar Parquet backup in `backend/data/processed/`.
4. Bulk-load the rows into `public.marine_data` using PostgreSQL `COPY`.
5. Register or update the float metadata in `public.floats`.
6. Add the float to the in-memory knowledge graph.
