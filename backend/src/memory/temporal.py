"""
FloatChat AI â€” Temporal Memory & Recency Bias

Ocean data is highly seasonal. A query like "What is the temperature in the Arabian Sea?"
should prioritize RECENT data over historical data unless historical context is requested.

This module implements:
1. Recency-weighted scoring for retrieval
2. Temporal query expansion (e.g. "last year" -> "2023-03-12 to 2024-03-12")
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.database.postgres import run_sql  # type: ignore

log = logging.getLogger(__name__)

def apply_temporal_bias(results: List[Dict[str, Any]], decay_factor: float = 0.95) -> List[Dict[str, Any]]:
    """
    Apply a decay score to results based on their age.
    Score = BaseScore * (decay_factor ^ (years_old))
    """
    now = datetime.now()
    for res in results:
        time = res.get("time")
        if not time:
            continue
            
        if isinstance(time, str):
            try:
                time = datetime.fromisoformat(time.replace('Z', '+00:00'))
            except ValueError:
                continue
                
        days_old = (now - time).days
        years_old = days_old / 365.25
        
        # Apply exponentially decreasing bias
        res["temporal_score"] = float(pow(decay_factor, years_old))
        
        # If we have a vector score, combine them
        if "score" in res:
            res["combined_score"] = res["score"] * res["temporal_score"]
            
    # Re-sort by combined score if available
    if results and "combined_score" in results[0]:
        return sorted(results, key=lambda x: x["combined_score"], reverse=True)
    return results

def get_time_window(query: str) -> Tuple[datetime, datetime]:
    """Extract or default a time window for the query."""
    # This is a stub - in production, this would use regex or NLP to extract dates.
    # Defaulting to past 120 days for safety if not specified.
    now = datetime.now()
    return (now - timedelta(days=120), now)
