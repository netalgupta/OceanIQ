# VARUNA Predictive ML & Deep Sensor QC — Member 3 (Sahil Shah)

Two production-ready ML services with FastAPI endpoints, now wired to the
**live Supabase ARGO archives** (~3.96M observations, 2022 → present):

| Service | File | Endpoint | What it does |
|---|---|---|---|
| **MHW Forecaster** | `mhw_forecast.py` | `POST /api/v1/ml/forecast-mhw` | Predicts the SST-anomaly surface at T+7 / T+14 days from a 30-day 2°×2° grid (temp/salinity/DOXY), with per-cell 95% CI, hotspot coordinates, day-by-day series and a Hobday-style declaration probability |
| **Sensor QC Autoencoder** | `qc_autoencoder.py` | `POST /api/v1/ml/qc-detect` | Scores a raw ARGO cast (0–2000 dbar) with an unsupervised 1D-CNN autoencoder; returns reconstruction MSE, flagged depth levels, classified issue (`SALINITY_DRIFT` / `OPTICAL_BIOFOULING` / `PRESSURE_SPIKE`) and an Argo-style QC flag (1/3/4) |
| **Real-data store** | `argo_store.py` | — (library) | Time-routed access to BOTH Supabase projects: grid aggregation, climatology derivation, deep-cast extraction, disk/memory caching |

Both models load **once** at startup (`warmup()` in the app lifespan) — never per request.

---

## Environment (verified working)

```
Python 3.14.4   torch==2.13.0+cpu   numpy==2.5.2   pydantic==2.13.4
fastapi==0.141.1   pytest==9.1.1   psycopg[binary]==3.3.4   httpx==0.28.1
```

```powershell
cd backend
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt "torch==2.13.0+cpu" --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
copy ..\.env.example .env   # then fill in the Supabase DSNs
.venv\Scripts\python -m pytest tests\test_ml_models.py -v   # 30 tests, ~3 s
```

> **Note:** `requirements.txt` leaves `qdrant-client>=1.8.0` unpinned; versions ≥1.10 removed
> `SearchRequest`, which `src/rag/retriever.py` imports. Pin `qdrant-client==1.9.2`
> until the retriever is migrated to the query API.

---

## Real data architecture (dual-Supabase routing)

The Argo archive outgrew one free-tier project and is split by time:

```text
DB project A   2025-08-01 → present      (~1.59M rows, aws-0-ap-southeast-2)
DB project B   2022-01-01 → 2025-07-31   (~2.37M rows, aws-0-ap-northeast-2)
```

⚠️ **The physical mapping of URL → time window is SWAPPED relative to early team
docs**, so routing in `argo_store` is *content-based*: each DSN's actual
`[min(time), max(time)]` is probed once and cached; every query window is then
routed to the right project(s). A window straddling the boundary is served from
both and merged — callers never care which database holds what.

### Configuration

| Variable | Meaning |
|---|---|
| `VARUNA_ML_REAL_DATA=1` | Master switch: serve forecasts from live grids, enable real-climatology baselines |
| `VARUNA_ARGO_DB_URLS` | `;`-separated Postgres DSNs for the two projects (falls back to built-in defaults) |

Set these in `backend/.env` (gitignored) — pydantic-settings picks them up.
Without them (or when the DB is unreachable) every path degrades gracefully to
the physics-informed synthetic generators: **a demo never dies mid-request**.

### What the forecaster consumes in live mode

`argo_store.build_history_grid(basin, end_date)` returns exactly
`(30, 3, 12, 12)` `[sst_c, psal, doxy]`:

1. SQL aggregates near-surface observations (`pres ≤ 20 dbar`) into global
   2°×2° bins × day, server-side;
2. bins are mapped into each basin's canonical 12×12 grid (weighted means —
   several 2° bins can share one cell);
3. gap-filling: linear interpolation across days → inverse-distance spatial
   diffusion → no NaNs guaranteed;
4. coverage gate: ≥ 10% of cells must have direct observations or the basin
   falls back to synthetic;
5. result cached in memory + `cache/*.npz` with a 6 h TTL → warm inference
   is pure numpy (**measured 4–11 ms**, well under the 100 ms budget).

Anomaly baselines use `argo_store.build_climatology(basin)` — a per-cell
day-of-year SST climatology derived from the FULL multi-year archive
(cosine-interpolated between month midpoints), with the synthetic seasonal
formula filling never-observed cells. Responses carry
`data_source: "live_argo" | "custom_provider" | "live_argo_unavailable_synthetic_fallback"`.

---

## Retraining

### QC autoencoder on LIVE archives (~60 s CPU)

```powershell
.venv\Scripts\python -m src.ml.qc_autoencoder --epochs 60
```

Pipeline (`retrain_on_real_data()`):

1. Pull deep casts from BOTH projects — aggregation runs server-side
   (`array_agg` + `HAVING count(*)≥40 AND span≥1200 dbar`), so only complete
   profiles cross the network; ascending/descending twins deduped;
2. quality gates: finite values, plausible ranges, must reach ≥1800 dbar,
   **deep-water salinity sanity** (deepest-decile mean ∈ [33, 37.5] PSU —
   rejects garbage casts);
3. resample onto the 64-level log pressure grid;
4. train denoising-style on ~2,200 REAL casts + 700 synthetic casts
   (real anchors the manifold; synthetic keeps fault geometry explicit);
5. calibrate all detector thresholds on held-out clean synthetic **and**
   real validation casts;
6. **validation gate** before saving: on fresh evaluation sets, corrupted
   variants of BOTH synthetic and real base profiles must be flagged
   ≥ 90% with correct issue class, false positives ≤ 10%. On failure the
   previous checkpoint is left untouched.

Latest shipped checkpoint (`checkpoints/qc_autoencoder.pt`,
trained on 3,638 real casts available / 2,200 used):

| Mode | Detection rate | Correct-issue rate |
|---|---|---|
| SALINITY_DRIFT | 93.3% | 90.5% |
| OPTICAL_BIOFOULING | 100% | 100% |
| PRESSURE_SPIKE | 95.0% | 94.0% |

False positives: 3.0% (fresh synthetic) · 7.7% (held-out real).

### MHW forecaster (~22 s CPU)

```powershell
.venv\Scripts\python -c "from src.ml import train_forecast_model; train_forecast_model(epochs=10, n_samples=384)"
```

- Model: **TCN** (4 dilated causal Conv1d blocks, d=1..8) + spatial conv head.
  Chosen over ConvLSTM: covers the 30-day receptive field deterministically,
  trains ~20× faster on CPU, flat <100 ms inference.
- Training data remains physics-informed synthetic (see limitations); serving
  inputs in live mode are REAL observation grids. Retraining directly against
  observed next-week anomalies is the documented future-work item — the sparse
  near-surface sampling makes naive daily targets noisy.

---

## Threshold calibration (QC)

Every detector threshold is fit on held-out **clean** casts (synthetic + real):

| Detector | Statistic | Rule |
|---|---|---|
| `mse` | global reconstruction energy | mean + 3·std |
| `drift` | log-depth slope of physical salinity residual × mono³ | mean + 3·std |
| `biof_rms` | shallow temp-residual RMS (°C) | mean + 3·std |
| `biof_hf` | high-frequency shallow temp residual (°C) | mean + 3·std |
| `spike_z` | max global-z level | clean 99.9th percentile |
| `disc` | max second difference of raw curve (°C/PSU) | mean + 3·std |

Issue classification uses **relative exceedance**: the fault family whose bar
is overshot hardest wins. (A fixed priority order mislabeled strong biofouling
as spikes — sharp surface wiggles also trip the discontinuity test.)

Fault injection floors were recalibrated against measured REAL background
variability: natural thermohaline structure in live casts exceeds the old
synthetic-only noise floor, so drift ramps were raised to 0.45–0.90 PSU and
biofouling amplitudes to 0.9–2.2 °C to stay separable.

---

## Testing

```powershell
.venv\Scripts\python -m pytest tests\test_ml_models.py -v
```

30 tests: forecast contract/scenarios/latency, QC detection of all three fault
modes (synthetic bases), FastAPI happy paths + validation errors via TestClient,
and offline-safe coverage of the real-data plumbing (time-window routing across
the DB boundary, weighted bin→cell mapping, gap-fill guarantees, sparse-basin
rejection, deep-salinity gate, synthetic fallback on DB failure). Tests run
fully offline — `tests/conftest.py` forces `VARUNA_ML_REAL_DATA=0`.

## Swapping in real ARGO data

Already done end-to-end; remaining upgrade paths:

1. **Forecasting**: retrain the TCN against targets derived from the real
   archive's own weekly anomalies (needs a smoothed climatology first).
2. **QC**: automatic — rerun `python -m src.ml.qc_autoencoder` any time;
   it always pulls fresh casts from both live projects.

## Known limitations

- ⚠️ The TCN's weights are still trained on physics-informed synthetic data;
  only its serving inputs/climatology are live. Absolute anomaly magnitudes are
  demo-grade until retraining against observed anomaly evolution.
- Near-surface ARGO sampling covers ~10–16% of each basin grid over 30 days;
  the rest is gap-filled (documented interpolation, not observation).
- Fault injection magnitudes are set ABOVE real background variability, so
  weaker real-world faults (e.g., slow 0.05 PSU drift) will pass under the gate.
- Basin MHW thresholds are Hobday-style P90 proxies (constants in
  `mhw_forecast.py`), not empirically-derived climatologies.
- Database credentials live in `backend/.env` (gitignored) and as built-in
  defaults in `argo_store.DEFAULT_DSNS` for demo resilience — rotate before any
  public deployment.
