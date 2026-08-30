"""
FloatChat AI — Semantic RAG Chain

For conceptual/documentation questions that don't need SQL:
  "What causes upwelling in the Arabian Sea?"
  "Explain the Argo float measurement cycle"
  "What is the oxygen minimum zone?"

Pipeline:
  1. Expand query for BM25 recall
  2. Hybrid retrieval (BM25 + Qdrant)
  3. KG enrichment (add domain facts)
  4. Context assembly
  5. Grounded generation (Llama3)
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List

from src.rag.retriever import get_retriever  # type: ignore
from src.rag.query_rewriter import expand_query  # type: ignore
from src.rag.context_assembler import assemble_context  # type: ignore
from src.rag.generator import generate_semantic_answer  # type: ignore
from src.memory.knowledge_graph import get_related_context  # type: ignore
from src.observability.logger import PipelineTrace  # type: ignore


async def answer(
    question: str,
    trace: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Pure semantic RAG chain for conceptual questions.
    Returns: {answer_markdown, chunks_used, viz_specs: None}
    """
    # ── Step 1: Query expansion ───────────────────────────────────────────────
    expanded = expand_query(question)
    if trace:
        trace.log("REWRITE", f"Expanded: {expanded[:80]}")

    # ── Step 2: Hybrid retrieval ──────────────────────────────────────────────
    if trace:
        trace.log("VECTOR", "Hybrid retrieval (BM25 + Qdrant)")
    retriever = await get_retriever()
    result = await retriever.retrieve(expanded, top_k=10)
    chunks: List[Dict[str, Any]] = list(result)  # type: ignore
    
    # Apply temporal recency bias
    from src.memory.temporal import apply_temporal_bias  # type: ignore
    chunks = apply_temporal_bias(chunks)
    
    if trace:
        top: Dict[str, Any] = next(iter(chunks)) if chunks else {}
        trace.log("RERANK", f"{len(chunks)} chunks after temporal bias | top score: {top.get('combined_score', top.get('rerank_score', 0)):.3f}",
                  top_chunks=[str(c.get("text", ""))[:80] for c in chunks[:3]])  # type: ignore

    # ── Step 3: KG context ────────────────────────────────────────────────────
    # Extract entities from question for KG lookup
    kg_context = ""
    ocean_terms = ["arabian sea", "bay of bengal", "equator", "temperature",
                   "salinity", "oxygen", "chlorophyll", "nitrate", "upwelling",
                   "monsoon", "thermocline", "halocline"]
    matched = [t for t in ocean_terms if t in question.lower()]
    if matched:
        kg_context = get_related_context(matched[:3])  # type: ignore
        if kg_context and trace:
            trace.log("KG", f"KG enrichment: {kg_context[:80]}")  # type: ignore

    # Inject KG context as an extra chunk
    if kg_context:
        chunks.append({
            "text": kg_context,
            "payload": {"source": "knowledge_graph"},
            "rrf": 0.5,
            "rerank_score": 0.5,
            "temporal_score": 1.0,
            "combined_score": 0.5
        })

    # ── Step 4: Context Assembly ──────────────────────────────────────────────
    if trace:
        trace.log("CONTEXT", "Assembling and compressing context")
    assembled_context, source_refs = assemble_context(chunks, max_tokens=8000)
    
    # ── Step 5: Generate grounded answer ──────────────────────────────────────
    if trace:
        trace.log("NARRATE", "Generating grounded answer")
    answer_text = await generate_semantic_answer(question, assembled_context)
    if trace:
        trace.log("RESPONSE", f"Answer: {answer_text}")

    return {
        "answer_markdown": answer_text,
        "sql": None,
        "rows": [],
        "viz_specs": {"chart_type": None, "chart_data": None, "map_data": None},
        "float_ids": [],
        "chunks_used": len(chunks),
    }
