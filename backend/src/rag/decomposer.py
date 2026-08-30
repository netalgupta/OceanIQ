"""
FloatChat AI â€” Multi-Hop Query Decomposer

WHY multi-hop?
  "Compare salinity in Arabian Sea vs Bay of Bengal for the last 6 months
   AND find the nearest ARGO floats to Mumbai" is actually 3 separate queries:
    1. Salinity stats in Arabian Sea (last 6 months)
    2. Salinity stats in Bay of Bengal (last 6 months)
    3. Nearest floats to Mumbai

  A single LLM SQL call can't handle this properly â€” it either ignores parts
  or generates a monstrous JOIN that returns garbage.

  The decomposer splits â†’ executes each â†’ merges results into one response.
"""
from __future__ import annotations
import re
from typing import List, Tuple, Dict, Any
from itertools import islice

from src.llm.ollama_client import decompose_query  # type: ignore
from src.rag.query_rewriter import detect_intent_fast  # type: ignore


async def maybe_decompose(question: str) -> Tuple[bool, List[str]]:
    """
    Returns (was_decomposed, list_of_subqueries).
    If question is simple, returns (False, [question]).
    """
    intent = detect_intent_fast(question)
    if intent == "MULTI_HOP":
        # Ensure we always return a list of strings
        raw_sub = await decompose_query(question)
        if raw_sub:
            subqueries = [str(q) for q in raw_sub]
            if len(subqueries) > 1:
                return True, subqueries
    return False, [question]


def merge_multi_hop_answers(
    sub_answers: List[Dict[str, Any]],
    original_question: str,
) -> Dict[str, Any]:
    """
    Merge list of {answer_markdown, sql, rows, viz_specs} from sub-queries
    into one coherent response.
    """
    # Merge all rows
    all_rows = []
    all_sqls = []
    all_markdowns = []
    merged_viz = {"chart_type": None, "chart_data": None, "map_data": None}

    for i, ans in enumerate(sub_answers, 1):
        rows = ans.get("rows") or []
        all_rows.extend(rows)
        if ans.get("sql"):
            all_sqls.append(f"-- Sub-query {i}\n{ans['sql']}")
        md = ans.get("answer_markdown","")
        if md:
            all_markdowns.append(f"**Part {i}:**\n{md}")
        # Use first non-None viz spec
        if not merged_viz["map_data"] and ans.get("viz_specs",{}).get("map_data"):
            merged_viz["map_data"] = ans["viz_specs"]["map_data"]
        if not merged_viz["chart_type"] and ans.get("viz_specs",{}).get("chart_type"):
            merged_viz["chart_type"] = ans["viz_specs"]["chart_type"]
            merged_viz["chart_data"] = ans["viz_specs"]["chart_data"]

    combined_md = "\n\n---\n\n".join(all_markdowns)
    combined_sql = "\n\n".join(all_sqls)

    return {
        "answer_markdown": combined_md,
        "sql": combined_sql,
        "rows": list(islice(all_rows, 500)),
        "viz_specs": merged_viz,
        "float_ids": sorted({str(r.get("platform_number")) for r in all_rows if r.get("platform_number")}),
    }
