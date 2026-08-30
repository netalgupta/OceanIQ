"""
FloatChat AI — Context Assembler

WHY context assembly?
  After retrieval you have N chunks ranked by relevance. You can't dump all of them
  into the LLM prompt — context window limits exist and more text ≠ better answers.

  The assembler:
    1. Deduplicates overlapping chunks (same doc, adjacent positions)
    2. Removes chunks below a relevance threshold
    3. Orders remaining chunks logically (by source type: schema first, then docs)
    4. Truncates to a token budget
    5. Returns a clean string ready for the LLM system prompt
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from src.config import settings  # type: ignore


def assemble_context(
    chunks: List[Dict[str, Any]],
    max_tokens: Optional[int] = None,
    min_score: float = 0.05,
) -> str:
    """
    Build a clean context string from ranked retrieval chunks.

    Args:
        chunks: list of {text, payload, rrf, rerank_score, ...} from retriever
        max_tokens: rough token budget (1 token ≈ 4 chars)
        min_score: drop chunks below this RRF score

    Returns:
        Formatted context string with source annotations.
    """
    max_tokens = max_tokens or settings.rag_max_context_tokens
    max_chars = max_tokens * 4  # rough conversion

    if not chunks:
        return ""

    # ── Step 1: Filter by minimum score ──────────────────────────────────────
    filtered = [c for c in chunks if c.get("rrf", 0) >= min_score or c.get("rerank_score", 0) >= 0.3]
    if not filtered:
        filtered = chunks[:3]  # type: ignore

    # ── Step 2: Deduplicate by text similarity ────────────────────────────────
    seen_texts: List[str] = []
    unique = []
    for chunk in filtered:
        text = chunk.get("text", "").strip()
        if not text:
            continue
        # Skip if very similar to a previously seen chunk (first 100 chars match)
        fingerprint = re.sub(r"\s+", " ", text[:120].lower())
        if any(fingerprint in seen or seen in fingerprint for seen in seen_texts):
            continue
        seen_texts.append(fingerprint)
        unique.append(chunk)

    # ── Step 3: Sort logically ────────────────────────────────────────────────
    # Priority: schema/primer docs first, then ocean variable docs, then summaries
    def _sort_key(c: Dict[str, Any]) -> int:
        src = (c.get("payload") or {}).get("source", "")
        if src in ("schema", "primer", "variables"):
            return 0
        if src in ("argo_paper", "documentation", "bgc"):
            return 1
        return 2  # float_summary, raw_chunk, etc.

    ordered = sorted(unique, key=_sort_key)

    # ── Step 4: Truncate to budget ────────────────────────────────────────────
    parts = []
    total_chars: int = 0
    for chunk in ordered:
        text = chunk.get("text", "").strip()
        source = (chunk.get("payload") or {}).get("source", "document")
        score = chunk.get("rerank_score", chunk.get("rrf", 0))
        header = f"[Source: {source} | relevance: {score:.3f}]"
        entry = f"{header}\n{text}"
        
        if total_chars + len(entry) > max_chars:  # type: ignore
            # Include a truncated version if space allows
            remaining = max_chars - total_chars - len(header) - 10  # type: ignore
            if remaining > 100:
                parts.append(f"{header}\n{text[:remaining]}...")  # type: ignore
            break
        parts.append(entry)
        total_chars += len(entry)  # type: ignore

    return "\n\n---\n\n".join(parts)
