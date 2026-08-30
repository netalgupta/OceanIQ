"""
FloatChat AI â€” Knowledge Graph Memory

WHY a knowledge graph?
  SQL is great for precision queries. But relationships like:
    "float 1902367 operates in the Arabian Sea, which has seasonal upwelling,
     which correlates with high doxy in June-September"
  ... are hard to express in flat SQL rows.

  A graph naturally represents: float â†’ region â†’ variable â†’ seasonal_pattern.
  We use NetworkX (in-process, no extra DB) for the KG because:
  - Our graph is small (~1000 nodes max for Indian Ocean ARGO)
  - NetworkX has rich traversal algorithms (BFS, shortest path, centrality)
  - It can be serialized to JSON and rebuilt on startup from Postgres

WHY NetworkX over Neo4j?
  Neo4j is awesome but requires another Docker container and its own query
  language (Cypher). For this scale, NetworkX loaded from DB at startup is
  faster, simpler, and sufficient.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx  # type: ignore

from src.database.postgres import run_sql  # type: ignore

# ━━ In-process KG ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_KG: Optional[nx.DiGraph] = None


def get_kg() -> nx.DiGraph:
    global _KG
    if _KG is None:
        _KG = nx.DiGraph()
        _seed_default_graph(_KG)
    return _KG


def _seed_default_graph(G: nx.DiGraph):
    """
    Seed with known ARGO domain relationships.
    In production, this is augmented with data from Postgres (kg_edges table).
    """
    # Ocean regions
    for region in ["arabian_sea", "bay_of_bengal", "equatorial_io", "indian_ocean"]:
        G.add_node(region, type="region")

    # Variables
    for var in ["temp", "psal", "doxy", "chla", "nitrate", "ph", "bbp700"]:
        G.add_node(var, type="variable")

    # Region â†’ Variable relationships (key science)
    G.add_edge("arabian_sea", "doxy",    rel="low_oxygen_zone",  weight=0.9)
    G.add_edge("arabian_sea", "temp",    rel="seasonal_sst",     weight=0.8)
    G.add_edge("arabian_sea", "chla",    rel="upwelling_bloom",  weight=0.7)
    G.add_edge("bay_of_bengal", "psal",   rel="freshwater_input", weight=0.9)
    G.add_edge("bay_of_bengal", "temp",   rel="warm_pool",        weight=0.8)
    G.add_edge("equatorial_io", "temp",   rel="itcz_dynamics",    weight=0.7)
    G.add_edge("equatorial_io", "doxy",   rel="io_eddy",          weight=0.6)

    # Variable correlations
    G.add_edge("temp", "doxy",    rel="inversely_correlated", weight=0.8)
    G.add_edge("chla", "nitrate", rel="nutrient_limiting",    weight=0.7)
    G.add_edge("psal", "temp",    rel="density_coupled",      weight=0.85)


def rebuild_kg_from_db():
    """Load KG edges from Postgres kg_edges table and add to graph."""
    G = get_kg()
    try:
        edges = run_sql("SELECT src_type, src_id, rel, dst_type, dst_id, weight FROM public.kg_edges LIMIT 5000")
        for e in edges:
            src = f"{e['src_type']}:{e['src_id']}"
            dst = f"{e['dst_type']}:{e['dst_id']}"
            G.add_node(src, type=e["src_type"])
            G.add_node(dst, type=e["dst_type"])
            G.add_edge(src, dst, rel=e["rel"], weight=float(e["weight"] or 1.0))
    except Exception:
        pass


def add_float_node(platform_number: int, region: str, variables: List[str]):
    """Register a float in the KG after ingestion."""
    G = get_kg()
    float_id = f"float:{platform_number}"
    G.add_node(float_id, type="float", platform=platform_number)
    G.add_edge(float_id, region, rel="operates_in", weight=1.0)
    for var in variables:
        G.add_edge(float_id, var, rel="measures", weight=1.0)


def get_related_context(query_entities: List[str]) -> str:
    """
    Traverse KG from query entities to find related facts.
    Returns a compact string injected into RAG context.
    """
    G = get_kg()
    facts = []
    for entity in query_entities:
        # Normalize entity name
        ent = entity.lower().replace(" ", "_")
        if ent not in G:
            # Try partial match
            matches = [n for n in G.nodes if ent in str(n)]
            if matches:
                ent = matches[0]
            else:
                continue

        # Get neighbors (1-hop relationships)
        for neighbor in G.neighbors(ent):
            edge = G.edges[ent, neighbor]
            rel = str(edge.get("rel", "related_to"))
            weight = edge.get("weight", 1.0)
            n_type = G.nodes[neighbor].get("type", "entity")
            facts.append(f"- {ent} {rel.replace('_', ' ')} {neighbor} (confidence: {weight:.1f})")

    if not facts:
        return ""
    return "Knowledge Graph context:\n" + "\n".join(facts[:10])  # type: ignore

def get_float_region(platform_number: int) -> Optional[str]:
    """Get the region a float primarily operates in."""
    G = get_kg()
    float_id = f"float:{platform_number}"
    if float_id not in G:
        return None
    for neighbor in G.neighbors(float_id):
        if G.nodes[neighbor].get("type") == "region":
            return neighbor
    return None
