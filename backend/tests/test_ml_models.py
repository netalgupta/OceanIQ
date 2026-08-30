"""
Unit & integration tests for VARUNA Member 3 — Predictive ML & Deep Sensor QC.
Covers: MHW forecast contract/scenarios/latency, QC autoencoder detection of all
three synthetic failure modes, and the FastAPI endpoints via TestClient.

Run:  pytest backend/tests/test_ml_models.py -v
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.ml import (
    MHWForecastRequest,
    ProfileQCRequest,
    corrupt_profile,
    evaluate_profile,
    generate_clean_profile,
    ml_router,
    predict_mhw_trend,
    set_history_provider,
    warmup,
)
from src.ml.mhw_forecast import BASIN_WINDOWS, generate_synthetic_history
from src.ml.qc_autoencoder import P_GRID

BASINS = ("arabian_sea", "bay_of_bengal", "equatorial_io")
CORRUPTION_MODES = ("SALINITY_DRIFT", "OPTICAL_BIOFOULING", "PRESSURE_SPIKE")


@pytest.fixture(scope="session", autouse=True)
def _loaded_models() -> None:
    """Load both model artifacts exactly once for the whole session."""
    assert warmup() is True


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(ml_router)
    return TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Deliverable 1 — MHW forecasting
# ─────────────────────────────────────────────────────────────────────────────


def _mhw_active_provider(basin: str, end_date):
    """History provider injecting an established, still-growing MHW event."""
    return generate_synthetic_history(
        basin, end_date, seed=123, inject_mhw=True, active_at_end=True
    )


@pytest.mark.parametrize("basin", BASINS)
def test_forecast_contract_and_calm_probability(basin: str) -> None:
    res = predict_mhw_trend(MHWForecastRequest(ocean_basin=basin, forecast_days=7))

    assert res.ocean_basin == basin
    assert res.forecast_horizon_days == 7
    assert len(res.time_series_forecast) == 7
    assert 0.0 <= res.mhw_probability <= 1.0
    # Calm default provider must yield LOW heatwave probability
    assert res.mhw_probability < 0.20

    day = res.time_series_forecast[0]
    assert {"date", "predicted_sst", "anomaly", "ci95_low", "ci95_high"} <= set(day)
    assert day["ci95_low"] <= day["anomaly"] <= day["ci95_high"]

    hotspot = res.max_anomaly_hotspot
    assert {"lat", "lon", "predicted_anomaly"} <= set(hotspot)
    lat0, lat1, lon0, lon1 = BASIN_WINDOWS[basin]
    assert lat0 <= hotspot["lat"] <= lat1
    assert lon0 <= hotspot["lon"] <= lon1


def test_known_mhw_event_yields_high_probability() -> None:
    set_history_provider(_mhw_active_provider)
    try:
        res = predict_mhw_trend(
            MHWForecastRequest(ocean_basin="bay_of_bengal", forecast_days=7)
        )
    finally:
        set_history_provider(None)

    assert res.mhw_probability > 0.30          # sane declaration threshold
    assert res.predicted_mean_anomaly > 0.30   # basin warms meaningfully
    assert res.max_anomaly_hotspot["predicted_anomaly"] > 1.00


def test_14_day_horizon_supported() -> None:
    res = predict_mhw_trend(
        MHWForecastRequest(ocean_basin="equatorial_io", forecast_days=14)
    )
    assert res.forecast_horizon_days == 14
    assert len(res.time_series_forecast) == 14


def test_lat_lon_subwindow_respected() -> None:
    lat_range = (8.0, 14.0)
    lon_range = (60.0, 70.0)
    res = predict_mhw_trend(
        MHWForecastRequest(
            ocean_basin="arabian_sea",
            forecast_days=7,
            lat_range=lat_range,
            lon_range=lon_range,
        )
    )
    hs = res.max_anomaly_hotspot
    assert lat_range[0] <= hs["lat"] <= lat_range[1]
    assert lon_range[0] <= hs["lon"] <= lon_range[1]


def test_invalid_inputs_raise_value_error() -> None:
    with pytest.raises(ValueError):
        predict_mhw_trend(MHWForecastRequest(ocean_basin="atlantic_ocean"))
    with pytest.raises(ValueError):
        predict_mhw_trend(
            MHWForecastRequest(ocean_basin="arabian_sea", forecast_days=10)
        )


def test_warm_inference_latency_under_100ms() -> None:
    predict_mhw_trend(MHWForecastRequest(ocean_basin="arabian_sea"))  # warm-up
    t0 = time.perf_counter()
    res = predict_mhw_trend(MHWForecastRequest(ocean_basin="arabian_sea"))
    wall_ms = (time.perf_counter() - t0) * 1000.0
    assert wall_ms < 100.0, f"inference took {wall_ms:.1f} ms"
    assert res.model_latency_ms < 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Deliverable 2 — Sensor QC autoencoder
# ─────────────────────────────────────────────────────────────────────────────


def _qc_request(mode: Optional[str] = None, seed: int = 7) -> ProfileQCRequest:
    temps, salts = generate_clean_profile(seed=seed)
    if mode is not None:
        temps, salts = corrupt_profile(temps, salts, mode, seed=seed + 1)
    return ProfileQCRequest(
        platform_number=1902303,
        pressures=list(P_GRID),
        temperatures=[float(x) for x in temps],
        salinities=[float(x) for x in salts],
    )


def test_clean_profile_passes_qc() -> None:
    res = evaluate_profile(_qc_request(seed=21))
    assert res.is_anomalous is False
    assert res.recommended_qc_flag == 1
    assert res.detected_issue is None
    assert res.flagged_depth_levels == []
    assert res.reconstruction_mse >= 0.0


@pytest.mark.parametrize("mode", CORRUPTION_MODES)
def test_corrupted_profiles_flagged_with_correct_issue(mode: str) -> None:
    res = evaluate_profile(_qc_request(mode=mode, seed=11))
    assert res.is_anomalous is True
    assert res.detected_issue == mode
    assert res.recommended_qc_flag in (3, 4)
    assert len(res.flagged_depth_levels) > 0


def test_pressure_spike_is_hard_failure_flag4() -> None:
    res = evaluate_profile(_qc_request(mode="PRESSURE_SPIKE", seed=31))
    assert res.recommended_qc_flag == 4


def test_multiple_clean_seeds_all_pass() -> None:
    for seed in range(40, 52):
        res = evaluate_profile(_qc_request(seed=seed))
        assert not res.is_anomalous, f"clean seed {seed} flagged (mse={res.reconstruction_mse})"


def test_qc_input_validation_errors() -> None:
    base = _qc_request()
    mismatched = ProfileQCRequest(
        platform_number=base.platform_number,
        pressures=base.pressures[:-1],
        temperatures=base.temperatures,
        salinities=base.salinities,
    )
    with pytest.raises(ValueError):
        evaluate_profile(mismatched)

    too_short = ProfileQCRequest(
        platform_number=1,
        pressures=[5.0, 10.0, 20.0],
        temperatures=[29.0, 28.8, 28.0],
        salinities=[35.6, 35.6, 35.7],
    )
    with pytest.raises(ValueError):
        evaluate_profile(too_short)


# ─────────────────────────────────────────────────────────────────────────────
# Deliverable 3 — FastAPI service endpoints (/api/v1/ml/*)
# ─────────────────────────────────────────────────────────────────────────────


def test_endpoint_forecast_happy_path(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/ml/forecast-mhw",
        json={"ocean_basin": "arabian_sea", "forecast_days": 7},
    )
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "ocean_basin",
        "forecast_horizon_days",
        "predicted_mean_anomaly",
        "max_anomaly_hotspot",
        "time_series_forecast",
        "mhw_probability",
    ):
        assert key in body
    assert body["forecast_horizon_days"] == 7
    assert 0.0 <= body["mhw_probability"] <= 1.0


def test_endpoint_forecast_unknown_basin_is_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/ml/forecast-mhw",
        json={"ocean_basin": "pacific_ocean"},
    )
    assert resp.status_code == 422


def test_endpoint_forecast_bad_types_is_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/ml/forecast-mhw",
        json={"ocean_basin": 12345, "forecast_days": "seven"},
    )
    assert resp.status_code == 422


def test_endpoint_qc_happy_path(client: TestClient) -> None:
    req = _qc_request(seed=77)
    resp = client.post(
        "/api/v1/ml/qc-detect",
        json={
            "platform_number": req.platform_number,
            "pressures": req.pressures,
            "temperatures": req.temperatures,
            "salinities": req.salinities,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "platform_number",
        "is_anomalous",
        "reconstruction_mse",
        "flagged_depth_levels",
        "detected_issue",
        "recommended_qc_flag",
    ):
        assert key in body
    assert body["recommended_qc_flag"] == 1


def test_endpoint_qc_corrupted_flags_anomaly(client: TestClient) -> None:
    req = _qc_request(mode="SALINITY_DRIFT", seed=13)
    resp = client.post(
        "/api/v1/ml/qc-detect",
        json={
            "platform_number": req.platform_number,
            "pressures": req.pressures,
            "temperatures": req.temperatures,
            "salinities": req.salinities,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_anomalous"] is True
    assert body["detected_issue"] == "SALINITY_DRIFT"


def test_endpoint_qc_mismatched_arrays_is_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/ml/qc-detect",
        json={
            "platform_number": 1902303,
            "pressures": [5.0, 10.0, 500.0],
            "temperatures": [29.4],
            "salinities": [35.6],
        },
    )
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Real-data integration — src.ml.argo_store routing / grid building
# (all tests here are OFFLINE: databases are simulated via monkeypatching)
# ─────────────────────────────────────────────────────────────────────────────

from datetime import date, datetime  # noqa: E402

import numpy as np  # noqa: E402

from src.ml import argo_store  # noqa: E402


def test_configured_dsns_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VARUNA_ARGO_DB_URLS", "postgresql://a; postgresql://b")
    assert argo_store.configured_dsns() == ["postgresql://a", "postgresql://b"]
    monkeypatch.setenv("VARUNA_ARGO_DB_URLS", "")
    # falls back to built-in defaults (or settings) without raising
    assert isinstance(argo_store.configured_dsns(), list)


def test_routed_window_splits_by_probed_range(monkeypatch: pytest.MonkeyPatch) -> None:
    ranges = {
        argo_store.DEFAULT_DSNS[0]: (datetime(2025, 8, 1), datetime(2026, 8, 21)),
        argo_store.DEFAULT_DSNS[1]: (datetime(2022, 1, 1), datetime(2025, 7, 31)),
    }
    monkeypatch.setattr(argo_store, "probe_range", lambda dsn: ranges[dsn])
    win = argo_store.RoutedWindow(datetime(2025, 7, 15), datetime(2025, 8, 15))
    assert len(win.segments) == 2
    hosts = {dsn.split("@")[-1].split(".")[0] for dsn, _, _ in win.segments}
    assert len(hosts) == 2  # window straddling the boundary hits BOTH projects
    for _, seg_start, seg_end in win.segments:
        assert seg_start <= seg_end


def test_routed_window_raises_when_uncovered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        argo_store, "configured_dsns", lambda: ["postgresql://only-one"]
    )
    monkeypatch.setattr(
        argo_store,
        "probe_range",
        lambda dsn: (datetime(2025, 1, 1), datetime(2025, 2, 1)),
    )
    try:
        argo_store.RoutedWindow(datetime(2026, 1, 1), datetime(2026, 2, 1))
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "No ARGO database covers" in str(exc)


def _fake_grid_rows(day: date, n_cells: int = 30) -> list:
    """Canned SQL aggregation rows for the Arabian Sea window.

    la_bin / lo_bin are GLOBAL 2°-bin indices as produced by
    floor(latitude/2)::int — i.e. lat 6..24°N -> bins 3..11,
    lon 52..74°E -> bins 26..36.
    """
    import datetime as dt

    rows = []
    for i in range(n_cells):
        rows.append(
            {
                "la_bin": float(3 + i // 10),
                "lo_bin": float(26 + (i % 10)),
                "day": day - dt.timedelta(days=i % 3),
                "temp": 28.0 + i * 0.01,
                "psal": 35.0 + i * 0.005,
                "doxy": 200.0 - i,
                "n": 10 + i,
            }
        )
    return rows


def test_build_history_grid_shape_and_fill(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    end = date.today()
    monkeypatch.setattr(argo_store, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(argo_store, "_MEM_CACHE", {})
    monkeypatch.setattr(
        argo_store,
        "fetch_daily_cell_stats",
        lambda basin, ed, lookback_days=40: _fake_grid_rows(ed),
    )
    res = argo_store.build_history_grid("arabian_sea", end)
    grid = res["grid"]
    assert grid.shape == (argo_store.HISTORY_DAYS, argo_store.N_VARS,
                          argo_store.GRID_H, argo_store.GRID_W)
    assert np.isfinite(grid).all(), "gap-filling must leave no NaNs"
    assert res["source"] == "live_argo"
    assert 0.0 < res["coverage"] <= 1.0
    assert grid[:, 0].min() > 20.0 and grid[:, 0].max() < 32.0  # sane SST band


def test_build_history_grid_rejects_sparse_basins(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(argo_store, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(argo_store, "_MEM_CACHE", {})
    monkeypatch.setattr(
        argo_store, "fetch_daily_cell_stats", lambda basin, ed, lookback_days=40: []
    )
    with pytest.raises(RuntimeError, match="No real ARGO observations"):
        argo_store.build_history_grid("arabian_sea")


def test_clean_real_profiles_deep_salinity_gate() -> None:
    p_grid = np.geomspace(2.5, 2000.0, argo_store.MIN_LEVELS + 5)
    deep_p = np.linspace(100.0, 2000.0, argo_store.MIN_LEVELS + 5)
    good_t = np.linspace(29.0, 4.0, len(deep_p))
    casts = [
        {"platform": 1, "cycle": 1, "dir": "A",
         "pres": deep_p.copy(),
         "temp": good_t.copy(),
         "psal": np.full(len(deep_p), 35.0)},                     # healthy
        {"platform": 2, "cycle": 1, "dir": "A",
         "pres": deep_p.copy(),
         "temp": good_t.copy(),
         "psal": np.full(len(deep_p), 14.5)},                     # garbage cast
    ]
    kept = argo_store.clean_real_profiles(casts, p_grid)
    assert len(kept) == 1  # the deep-salinity sanity gate rejected cast #2
    assert kept[0][1].min() > 34.0


def test_db_history_provider_falls_back_to_synthetic(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.ml.mhw_forecast import db_history_provider

    def boom(*a, **k):
        raise RuntimeError("database unreachable")

    monkeypatch.setattr(argo_store, "build_history_grid", boom)
    hist = db_history_provider("arabian_sea", date.today())
    assert hist.shape == (argo_store.HISTORY_DAYS, argo_store.N_VARS,
                          argo_store.GRID_H, argo_store.GRID_W)
    assert np.isfinite(hist).all()


def test_real_data_disabled_by_default_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VARUNA_ML_REAL_DATA", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests::test_real_data_disabled_by_default")
    monkeypatch.delenv("VARUNA_TEST_ALLOW_REAL_DATA", raising=False)
    assert argo_store.real_data_enabled() is False


def test_enable_real_data_offline_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """enable_real_data(True) must degrade gracefully when no DB is reachable."""
    from src.ml import mhw_forecast as mf

    def dead_status():
        return {"databases": [{"host": "x", "reachable": False, "error": "boom"}]}

    monkeypatch.setattr(argo_store, "status", dead_status)
    try:
        ok = mf.enable_real_data(True)
        assert ok is False
        assert mf.real_data_active() is False
        # forecasting still works on the synthetic path
        res = predict_mhw_trend(MHWForecastRequest(ocean_basin="arabian_sea"))
        assert 0.0 <= res.mhw_probability <= 1.0
    finally:
        mf.enable_real_data(False)  # restore deterministic synthetic default
