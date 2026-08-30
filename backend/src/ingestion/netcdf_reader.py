"""
FloatChat AI — NetCDF Ingestion Pipeline

Converts ARGO NetCDF files → Parquet → PostgreSQL → Qdrant embeddings.

WHY this order?
  NetCDF → Parquet: columnar storage, 10x smaller than NetCDF, DuckDB-queryable
  Parquet → PostgreSQL: for SQL queries (the main data path)
  PostgreSQL → Qdrant: float summaries as embeddings for semantic search

WHY netCDF4 library?
  The ARGO files use NetCDF-4 format (HDF5 underneath). The netCDF4 Python
  library is the official reader maintained by Unidata — the same org that
  manages THREDDS and OPeNDAP. It handles fill values, QC flags, and
  variable attributes correctly.

WHY Parquet as intermediate?
  - Apache Parquet is columnar → reads only the columns you need
  - DuckDB can query Parquet directly without loading into Postgres
  - Parquet preserves dtypes (float32 for measurements, preserving precision)
  - Serves as a permanent raw archive of all ingested data
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime

import numpy as np  # type: ignore
import pyarrow as pa  # type: ignore
import pyarrow.parquet as pq  # type: ignore

log = logging.getLogger(__name__)


def read_argo_netcdf(filepath: str) -> Optional[pa.Table]:
    """
    Read a single ARGO NetCDF profile file and convert to PyArrow Table.

    ARGO file structure:
      Dimensions: N_PROF (profiles), N_LEVELS (depth levels per profile)
      Core variables: PRES, TEMP, PSAL, DOXY, CHLA, NITRATE, PH_IN_SITU_TOTAL
      Metadata: PLATFORM_NUMBER, JULD (Julian date), LATITUDE, LONGITUDE
      QC flags: TEMP_QC, PSAL_QC, etc. (char arrays, '1'=good, '4'=bad)
    """
    try:
        import netCDF4 as nc  # type: ignore
    except ImportError:
        log.error("netCDF4 not installed: pip install netCDF4")
        return None

    try:
        ds = nc.Dataset(filepath, "r")
    except Exception as e:
        log.error(f"Could not open {filepath}: {e}")
        return None

    try:
        n_prof   = ds.dimensions["N_PROF"].size
        n_levels = ds.dimensions["N_LEVELS"].size

        def _var(name: str, fill=np.nan) -> np.ndarray:
            """Extract a variable, masking fill values."""
            if name not in ds.variables:
                return np.full((n_prof, n_levels) if name not in ("PLATFORM_NUMBER","JULD","LATITUDE","LONGITUDE") else n_prof, fill)
            v = ds.variables[name]
            data = v[:]
            if hasattr(data, "filled"):
                data = data.filled(fill)
            return np.array(data)

        def _qc(name: str) -> np.ndarray:
            """Read QC flag array as int (char '1' → 1, '4' → 4)."""
            if name not in ds.variables:
                return np.zeros((n_prof, n_levels), dtype=np.int8)
            raw = ds.variables[name][:]
            if raw.dtype.kind in ("U", "S"):
                # Convert char QC to int
                flat = np.array([int(c) if c.strip().isdigit() else 0
                                 for c in raw.flatten()]).reshape(raw.shape)
                return flat.astype(np.int8)
            return np.array(raw, dtype=np.int8)

        # Platform number (N_PROF,)
        pnum_raw = ds.variables["PLATFORM_NUMBER"][:] if "PLATFORM_NUMBER" in ds.variables else None
        if pnum_raw is not None:
            # ARGO stores as char array of shape (N_PROF, 8)
            if pnum_raw.ndim == 2:
                pnum = np.array([
                    int("".join(r.astype(str)).strip()) if "".join(r.astype(str)).strip().isdigit() else 0
                    for r in pnum_raw
                ], dtype=np.int64)
            else:
                pnum = np.array(pnum_raw, dtype=np.int64)
        else:
            pnum = np.zeros(n_prof, dtype=np.int64)

        # Julian days → datetime
        juld_raw = _var("JULD", fill=np.nan).flatten()[:n_prof]
        from datetime import datetime, timedelta
        JULD_EPOCH = datetime(1950, 1, 1)
        times = []
        for j in juld_raw:
            try:
                times.append((JULD_EPOCH + timedelta(days=float(j))).isoformat() if not np.isnan(j) else None)
            except Exception:
                times.append(None)

        lat = _var("LATITUDE", fill=np.nan).flatten()[:n_prof]
        lon = _var("LONGITUDE", fill=np.nan).flatten()[:n_prof]

        # Core profile variables (N_PROF × N_LEVELS)
        PRES    = _var("PRES");    PRES_QC  = _qc("PRES_QC")
        TEMP    = _var("TEMP");    TEMP_QC  = _qc("TEMP_QC")
        PSAL    = _var("PSAL");    PSAL_QC  = _qc("PSAL_QC")
        DOXY    = _var("DOXY");    DOXY_QC  = _qc("DOXY_QC")
        CHLA    = _var("CHLA_ADJUSTED") if "CHLA_ADJUSTED" in ds.variables else _var("CHLA")
        NITRATE = _var("NITRATE_ADJUSTED") if "NITRATE_ADJUSTED" in ds.variables else _var("NITRATE")
        PH      = _var("PH_IN_SITU_TOTAL")
        BBP700  = _var("BBP700_ADJUSTED") if "BBP700_ADJUSTED" in ds.variables else _var("BBP700")

        # Flatten N_PROF × N_LEVELS into rows
        rows_pnum, rows_time, rows_lat, rows_lon = [], [], [], []
        rows_pres, rows_temp, rows_psal, rows_doxy = [], [], [], []
        rows_chla, rows_nitrate, rows_ph, rows_bbp = [], [], [], []
        rows_pres_qc, rows_temp_qc, rows_psal_qc, rows_doxy_qc = [], [], [], []

        for p in range(n_prof):
            for lv in range(n_levels):
                pres_val = float(PRES[p, lv]) if not np.isnan(PRES[p, lv]) else None  # type: ignore
                if pres_val is None:
                    continue  # skip empty levels
                rows_pnum.append(int(pnum[p]))  # type: ignore
                rows_time.append(times[p])  # type: ignore
                rows_lat.append(float(lat[p]) if not np.isnan(lat[p]) else None)  # type: ignore
                rows_lon.append(float(lon[p]) if not np.isnan(lon[p]) else None)  # type: ignore
                rows_pres.append(pres_val)
                rows_pres_qc.append(int(PRES_QC[p, lv]))  # type: ignore

                def _fv(arr: Any, pi: int, li: int) -> Optional[float]:
                    v = arr[pi, li]  # type: ignore
                    return float(v) if not np.isnan(v) else None

                rows_temp.append(_fv(TEMP, p, lv));   rows_temp_qc.append(int(TEMP_QC[p, lv]))  # type: ignore
                rows_psal.append(_fv(PSAL, p, lv));   rows_psal_qc.append(int(PSAL_QC[p, lv]))  # type: ignore
                rows_doxy.append(_fv(DOXY, p, lv));   rows_doxy_qc.append(int(DOXY_QC[p, lv]))  # type: ignore
                rows_chla.append(_fv(CHLA, p, lv))
                rows_nitrate.append(_fv(NITRATE, p, lv))
                rows_ph.append(_fv(PH, p, lv))
                rows_bbp.append(_fv(BBP700, p, lv))

        ds.close()

        table = pa.table({
            "platform_number": pa.array(rows_pnum, pa.int64()),
            "time":            pa.array(rows_time, pa.string()),
            "latitude":        pa.array(rows_lat,  pa.float64()),
            "longitude":       pa.array(rows_lon,  pa.float64()),
            "pres":            pa.array(rows_pres, pa.float32()),
            "pres_qc":         pa.array(rows_pres_qc, pa.int8()),
            "temp":            pa.array(rows_temp, pa.float32()),
            "temp_qc":         pa.array(rows_temp_qc, pa.int8()),
            "psal":            pa.array(rows_psal, pa.float32()),
            "psal_qc":         pa.array(rows_psal_qc, pa.int8()),
            "doxy":            pa.array(rows_doxy, pa.float32()),
            "doxy_qc":         pa.array(rows_doxy_qc, pa.int8()),
            "chla":            pa.array(rows_chla, pa.float32()),
            "nitrate":         pa.array(rows_nitrate, pa.float32()),
            "ph_in_situ_total":pa.array(rows_ph,   pa.float32()),
            "bbp700":          pa.array(rows_bbp,  pa.float32()),
        })
        log.info(f"Parsed {filepath}: {len(table)} measurement rows from {n_prof} profiles")
        return table

    except Exception as e:
        log.error(f"Error parsing {filepath}: {e}")
        if 'ds' in locals():
            try:
                ds.close()
            except Exception:
                pass
        return None


def save_parquet(table: pa.Table, output_dir: str, filename: str) -> str:
    """Save Arrow table to Parquet. Returns output path."""
    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, f"{filename}.parquet")
    pq.write_table(
        table, out,
        compression="snappy",        # fast compression, good ratio
        row_group_size=100_000,       # optimized for Parquet scan
    )
    log.info(f"Saved Parquet: {out} ({len(table)} rows)")
    return out
