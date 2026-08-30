"""
FloatChat AI â€” LLM-as-a-Reranker

WHY LLM-as-a-Reranker?
  Standard embedding cosine similarity (Bi-Encoders) is fast but misses nuances
  where the query and document use different vocabulary. A Cross-Encoder scoring
  candidate pairs (query, document) is much more accurate.
  
  Since we are running locally on an RTX 4060, we use a tiny, fast model 
  (Phi-3 3.8B) to score the top-12 candidates and pick the best 5.
"""
from __future__ import annotations
import logging
import json
import re
from typing import List, Dict, Any

from src.config import settings  # type: ignore
from src.llm.ollama_client import _generate  # type: ignore

log = logging.getLogger(__name__)

async def rerank_with_llm(
    query: str, 
    candidates: List[Dict[str, Any]], 
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """
    Use a small LLM (Phi-3) to score the relevance of context chunks.
    Prompt style: Rank list or point-wise scoring. 
    Point-wise is more robust for small models.
    """
    if not candidates:
        return []

    # If we only have 1-2 candidates, don't waste time reranking
    if len(candidates) <= 2:
        return candidates[:top_n]  # type: ignore

    scored_candidates = []
    
    # We batch candidates to minimize LLM calls, but limit batch size 
    # so the context window doesn't explode and cause slow inference.
    batch_size = 6
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i : i + batch_size]  # type: ignore
        
        prompt = (
            "You are an oceanographic data expert. Rate the relevance of each context chunk "
            f"to the user query: \"{query}\"\n\n"
        )
        for idx, cand in enumerate(batch):
            text = cand.get("text", "")[:400]  # type: ignore
            prompt += f"CHUNK {idx}:\n{text}\n---\n"
            
        prompt += (
            "\nOutput ONLY a JSON array of integers from 0-10, where 10 is highly relevant "
            "and 0 is irrelevant. Match the order of chunks exactly. Example: [8, 2, 9, 0...]"
        )
        
        try:
            # Use Phi-3 or similar small model configured in OLLAMA_REWRITE_MODEL
            response = await _generate(
                model=settings.ollama_rewrite_model,
                prompt=prompt,
                temperature=0.01,
            )
            
            # Extract JSON array
            match = re.search(r'\[[\d,\s]+\]', response)
            if match:
                scores = json.loads(match.group())
                for idx, score in enumerate(scores):
                    if idx < len(batch):
                        batch[idx]["rerank_score"] = float(score)
            else:
                # Fallback: assign decreasing scores if LLM fails
                for idx, cand in enumerate(batch):
                    cand["rerank_score"] = cand.get("rerank_score", 0.0)
                    
        except Exception as e:
            log.warning(f"Reranking batch failed: {e}")
            for cand in batch:
                cand["rerank_score"] = cand.get("rerank_score", 0.0)
        
        scored_candidates.extend(batch)

    # Sort by the new rerank_score
    reranked = sorted(
        scored_candidates, 
        key=lambda x: x.get("rerank_score", 0.0), 
        reverse=True
    )
    
    return reranked[:top_n]  # type: ignore
