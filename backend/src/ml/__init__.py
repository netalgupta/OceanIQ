"""
VARUNA — Predictive ML & Deep Sensor QC package (Member 3)
==========================================================

Owns:
- Spatio-Temporal Marine Heatwave Forecasting (TCN, 7/14-day)   -> src.ml.mhw_forecast
- Unsupervised 1D-CNN Autoencoder sensor QC / biofouling detect -> src.ml.qc_autoencoder
- Live dual-Supabase ARGO archive access (time-range routing)   -> src.ml.argo_store

Exposes `ml_router` (mounted under /api/v1/ml) and a `warmup()` hook that
loads both model artifacts exactly once at application startup. When
VARUNA_ML_REAL_DATA=1, warmup() additionally switches the forecaster onto
the live Supabase archives and prefetches grids/climatology so inference
stays < 100 ms; any database problem silently degrades to synthetic mode.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.ml.mhw_forecast import (  # noqa: F401
    MHWForecastRequest,
    MHWForecastResponse,
    VALID_BASINS,
    db_history_provider,
    enable_real_data,
    ensure_ready as ensure_forecast_ready,
    generate_synthetic_history,
    predict_mhw_trend,
    real_data_active,
    set_history_provider,
    train_model as train_forecast_model,
)
from src.ml.qc_autoencoder import (  # noqa: F401
    ProfileQCRequest,
    ProfileQCResponse,
    corrupt_profile,
    ensure_ready as ensure_qc_ready,
    evaluate_profile,
    generate_clean_profile,
    retrain_on_real_data,
    train_and_calibrate as train_qc_autoencoder,
)

ml_router = APIRouter(
    prefix="/api/v1/ml",
    tags=["🧠 Predictive ML & Deep Sensor QC"],
)


@ml_router.post(
    "/forecast-mhw",
    response_model=MHWForecastResponse,
    summary="7/14-Day Spatio-Temporal Marine Heatwave Forecast",
    description=(
        "Runs the trained Temporal Convolutional Network on the latest 30-day "
        "2°×2° physical grid (temp/salinity/DOXY) and returns the predicted SST "
        "anomaly surface at T+7 or T+14 days, per-cell 95% confidence bounds, "
        "hottest hotspot coordinates, day-by-day basin forecast series and an "
        "Hobday-style MHW declaration probability."
    ),
)
async def forecast_mhw(req: MHWForecastRequest) -> MHWForecastResponse:
    try:
        return predict_mhw_trend(req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 — surface clean 500s, never stack traces
        raise HTTPException(status_code=500, detail=f"MHW forecast inference failed: {exc}")


@ml_router.post(
    "/qc-detect",
    response_model=ProfileQCResponse,
    summary="Deep 1D-CNN Sensor QC & Biofouling Detection",
    description=(
        "Scores one raw ARGO cast with the unsupervised 1D-CNN autoencoder: "
        "returns reconstruction MSE, flagged depth levels and the classified "
        "sensor issue (SALINITY_DRIFT | OPTICAL_BIOFOULING | PRESSURE_SPIKE) "
        "with a recommended Argo-style QC flag (1/3/4)."
    ),
)
def qc_detect(req: ProfileQCRequest) -> ProfileQCResponse:
    try:
        return evaluate_profile(req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Sensor QC inference failed: {exc}")


def warmup(use_real_data: "bool | None" = None) -> bool:
    """
    Load both models once. Call from app lifespan/startup (not per-request).

    When `use_real_data` is None it defers to argo_store.real_data_enabled()
    (VARUNA_ML_REAL_DATA env / backend/.env). In real mode the forecaster is
    switched to the live Supabase archives and 30-day grids + multi-year
    climatology are prefetched for all three basins; any failure degrades
    gracefully to synthetic mode.
    """
    ok_forecast = ensure_forecast_ready()
    ok_qc = ensure_qc_ready()

    if use_real_data is None:
        from src.ml.argo_store import real_data_enabled

        use_real_data = real_data_enabled()
    real_ok = False
    if use_real_data:
        try:
            real_ok = enable_real_data(True)
            if real_ok:
                from src.ml import argo_store

                print(f"[ml] live ARGO archives active: {argo_store.status()}")
        except Exception as exc:  # noqa: BLE001 — startup must survive DB outage
            print(f"[ml] real-data activation failed ({exc}) — synthetic fallback")
    return bool(ok_forecast and ok_qc)


__all__ = [
    "MHWForecastRequest",
    "MHWForecastResponse",
    "ProfileQCRequest",
    "ProfileQCResponse",
    "VALID_BASINS",
    "corrupt_profile",
    "db_history_provider",
    "enable_real_data",
    "evaluate_profile",
    "generate_clean_profile",
    "generate_synthetic_history",
    "ml_router",
    "predict_mhw_trend",
    "real_data_active",
    "retrain_on_real_data",
    "set_history_provider",
    "train_forecast_model",
    "train_qc_autoencoder",
    "warmup",
]
