"""
FloatChat AI â€” Feedback & Reinforcement Memory

Handles the persistence and analysis of user feedback (ratings/corrections).
This data is used to:
1. Improve retrieval ranking (Feedback-weighted retrieval)
2. Fine-tune future models on corrected SQL/prose
3. Track system performance over time
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.database.postgres import store_feedback as db_store_feedback  # type: ignore

log = logging.getLogger(__name__)

async def process_user_feedback(
    session_id: str,
    query: str,
    rating: int,
    sql_generated: Optional[str] = None,
    answer: Optional[str] = None,
    correction: Optional[str] = None,
    trace: Optional[dict] = None
) -> int:
    """
    Process and store user feedback. 
    In Phase 5, this just persists to PostgreSQL. 
    In Phase 6, we'll implement logic to boost the 'weight' of correctly rated retrieval chunks.
    """
    try:
        feedback_id = db_store_feedback(
            session_id=session_id,
            query=query,
            sql_generated=sql_generated,
            answer=answer,
            rating=rating,
            correction=correction,
            pipeline_trace=trace
        )
        
        log.info(f"Feedback stored: ID={feedback_id} Rating={rating}")
        
        # If rating is bad (1-2) and we have a correction, log it for manual review
        if rating <= 2 and correction:
            log.warning(f"Negative feedback for query: {query}. Correction: {correction}")
            
        return feedback_id
        
    except Exception as e:
        log.error(f"Failed to store feedback: {e}")
        return -1

def get_feedback_stats() -> Dict[str, Any]:
    """Retrieve summary of system performance based on feedback."""
    from src.database.postgres import run_sql  # type: ignore
    try:
        stats = run_sql(
            "SELECT AVG(rating) as avg_rating, COUNT(*) as total_count FROM public.query_feedback"
        )
        return stats[0] if stats else {"avg_rating": 0, "total_count": 0}
    except Exception:
        return {"avg_rating": 0, "total_count": 0}
