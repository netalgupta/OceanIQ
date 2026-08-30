"""
VARUNA — Grounded Answer Generator
Grounded answer generation using OpenRouter Nemotron-Ultra 550B.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional
from src.llm.openrouter_client import chat_complete
from src.rag.context_assembler import assemble_context

GROUNDED_SYSTEM_PROMPT = """You are the Grounded Scientific Copilot for VARUNA (INCOIS & CMLRE).

STRICT RULES:
1. Answer ONLY using the provided oceanographic context and SQL results below.
2. If the context does not contain enough information, state what is missing clearly.
3. Always include key values with units (°C, PSU, µmol/kg, mg/m³), time window, and ocean region.
4. Format response in clean Markdown with headers.
5. Do NOT hallucinate data values.
"""


async def generate_grounded_answer(
    question: str,
    context_chunks: List[Dict[str, Any]],
    sql: Optional[str] = None,
    sql_rows: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False,
) -> str | AsyncIterator[str]:
    """
    Generate a grounded answer using retrieved context + SQL results.
    """
    context_str, _ = assemble_context(context_chunks)

    prompt = f"Question: {question}\n\nContext:\n{context_str}"
    if sql:
        prompt += f"\n\nExecuted SQL:\n```sql\n{sql}\n```"
    if sql_rows:
        prompt += f"\n\nSample Rows:\n{sql_rows[:5]}"

    messages = [
        {"role": "system", "content": GROUNDED_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    return await chat_complete(messages, temperature=0.1, task_tag="grounded_rag")


async def generate_semantic_answer(
    question: str,
    context: str,
) -> str:
    """
    Generate a pure semantic answer from retrieved ocean literature context.
    """
    messages = [
        {"role": "system", "content": GROUNDED_SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {question}\n\nRetrieved Scientific Context:\n{context}"},
    ]
    return await chat_complete(messages, temperature=0.1, task_tag="semantic_rag")
