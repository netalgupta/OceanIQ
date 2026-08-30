"""
FloatChat AI — Oceanographic Data Summarizer (Offline & Rule Fallback)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

def summarize_telemetry_rows(question: str, sql: str, rows: List[Dict[str, Any]]) -> str:
    """Generate concise scientific narration for returned ARGO observation rows."""
    if not rows:
        return "No telemetry records matched the query criteria in the dataset."

    count = len(rows)
    platforms = set()
    lats, lons = [], []
    temps, psals, doxys, chlas = [], [], [], []

    for r in rows:
        if r.get("platform_number"): platforms.add(r.get("platform_number"))
        if r.get("latitude") is not None: lats.append(float(r["latitude"]))
        if r.get("longitude") is not None: lons.append(float(r["longitude"]))
        if r.get("temp") is not None: temps.append(float(r["temp"]))
        if r.get("psal") is not None: psals.append(float(r["psal"]))
        if r.get("doxy") is not None: doxys.append(float(r["doxy"]))
        if r.get("chla") is not None: chlas.append(float(r["chla"]))

    lines = []
    lines.append(f"Analyzed **{count} observations** across **{len(platforms)} active ARGO float(s)**.")

    if lats and lons:
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        lines.append(f"**Geographic Coverage**: Latitude [{min_lat:.2f}° to {max_lat:.2f}°], Longitude [{min_lon:.2f}° to {max_lon:.2f}°].")

    metrics = []
    if temps:
        metrics.append(f"Temperature: **{sum(temps)/len(temps):.2f} °C** (range {min(temps):.2f}–{max(temps):.2f} °C)")
    if psals:
        metrics.append(f"Salinity: **{sum(psals)/len(psals):.2f} PSU** (range {min(psals):.2f}–{max(psals):.2f} PSU)")
    if doxys:
        metrics.append(f"Dissolved Oxygen: **{sum(doxys)/len(doxys):.2f} µmol/kg** (range {min(doxys):.2f}–{max(doxys):.2f} µmol/kg)")
    if chlas:
        metrics.append(f"Chlorophyll-a: **{sum(chlas)/len(chlas):.3f} mg/m³** (max {max(chlas):.3f} mg/m³)")

    if metrics:
        lines.append("**Key Oceanographic Parameters**:\n- " + "\n- ".join(metrics))

    return "\n\n".join(lines)
