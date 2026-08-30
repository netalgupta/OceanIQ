"""
FloatChat AI â€” User Personalization

Stores and retrieves user-specific settings:
- Preferred regions (e.g. 'Arabian Sea')
- Preferred variables (e.g. 'psal', 'temp')
- Default time windows
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

# type: ignore for IDE import issues
from src.database.postgres import run_sql, get_pool 

log = logging.getLogger(__name__)

def get_user_preferences(user_id: str) -> Dict[str, Any]:
    """Retrieve user preferences from PostgreSQL."""
    try:
        rows = run_sql(
            "SELECT regions, variables, time_range FROM public.user_preferences WHERE user_id = %(user_id)s",
            {"user_id": user_id}
        )
        if not rows:
            return {
                "regions": ["indian_ocean"],
                "variables": ["temp", "psal", "doxy"],
                "time_range": {"days": 120}
            }
        return rows[0]
    except Exception as e:
        log.error(f"Failed to fetch preferences for {user_id}: {e}")
        return {}

def save_user_preferences(user_id: str, prefs: Dict[str, Any]) -> bool:
    """Save or update user preferences."""
    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO public.user_preferences (user_id, regions, variables, time_range)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        regions = EXCLUDED.regions,
                        variables = EXCLUDED.variables,
                        time_range = EXCLUDED.time_range
                """
                cur.execute(
                    sql,
                    (
                        user_id,
                        json.dumps(prefs.get("regions", [])),
                        json.dumps(prefs.get("variables", [])),
                        json.dumps(prefs.get("time_range", {}))
                    )
                )
                conn.commit()
        return True
    except Exception as e:
        log.error(f"Failed to save preferences for {user_id}: {e}")
        return False
