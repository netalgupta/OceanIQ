"""
FloatChat AI — Query Intent Detection & Rewriting

WHY a dedicated query rewriter?
  Raw user queries are often ambiguous: "show me something near Kochi last week"
  doesn't tell you if they want a map, depth profile, or table.
  The rewriter:
    1. Detects intent (which pipeline to invoke)
    2. Rewrites → more specific, SQL-friendly form
    3. Expands ocean-domain synonyms

Intent classes:
  SQL_DATA       → generate SQL + run on Postgres
  NEAREST_FLOAT  → deterministic PostGIS radius query (no LLM sql needed)
  SEMANTIC       → Qdrant RAG search (for conceptual/doc questions)
  SMALLTALK      → greet/math/time, handled in-server
  MULTI_HOP      → decompose into sub-queries
"""
from __future__ import annotations
import re
from typing import Tuple

# ── Pattern-based fast-path intent (no LLM needed for these) ─────────────────
_MATH_RE     = re.compile(r"^[\d\s\+\-\*\/\%\^\(\)\.√]+$")
_TIME_RE     = re.compile(r"^\s*(time|current time|what.?s the time)\??\s*$", re.I)
_HELLO_RE    = re.compile(r"^\s*(hi|hello|hey|namaste|yo|greetings|howdy)\s*$", re.I)
_NEAREST_RE  = re.compile(
    r"\b(nearest|closest|near|around|nearby)\b.*(float|buoy|argo|platform)", re.I
)
_NEAR_ME_RE  = re.compile(r"\b(near me|around me|my location)\b", re.I)

_DATA_TOKENS = frozenset([
    "temp","temperature","psal","salinity","doxy","oxygen","chla","chlorophyll",
    "nitrate","ph","pressure","depth","profile","pres","bbp","backscatter",
    "float","buoy","platform","argo","wmo",
    "arabian sea","bay of bengal","equator","indian ocean",
    "mumbai","kochi","chennai","goa","visakhapatnam","kolkata","kerala",
    "lat","lon","latitude","longitude","coord","coordinate",
    "month","week","day","year","trend","average","avg","max","min",
    "compare","seasonal","anomaly","cycle","trajectory","track",
])

_SEMANTIC_TOKENS = frozenset([
    "explain","what is","what are","why","how does","tell me about",
    "upwelling","mixed layer","thermocline","halocline","pycnocline",
    "monsoon","eddies","gyres","circulation","current","bgc","biogeochemical",
    "argo program","argo float","netcdf","ctd","glider",
    "literature","research","paper","study","dataset","documentation",
])


def detect_intent_fast(query: str) -> str:
    """
    Rule-based fast-path intent detection (no LLM call).
    Returns intent string or empty string if uncertain.
    """
    q = query.strip()
    ql = q.lower()

    if _HELLO_RE.match(q):
        return "SMALLTALK"
    if _TIME_RE.match(q):
        return "SMALLTALK"
    if _MATH_RE.match(q) and any(op in q for op in "+-*/%^"):
        return "SMALLTALK"
    if _NEAR_ME_RE.search(ql):
        return "NEAREST_FLOAT"
    if _NEAREST_RE.search(ql):
        return "NEAREST_FLOAT"

    # Check for data tokens
    data_hits = sum(1 for tok in _DATA_TOKENS if tok in ql)
    sem_hits  = sum(1 for tok in _SEMANTIC_TOKENS if tok in ql)

    if data_hits > 0 and data_hits >= sem_hits:
        # Multi-hop if query has 'and' connecting multiple data requests
        if re.search(r"\band\b.*(compare|also|additionally|nearest|find)", ql):
            return "MULTI_HOP"
        return "SQL_DATA"
    if sem_hits > 0:
        return "SEMANTIC"

    return ""  # uncertain → let LLM decide


# Ocean domain synonyms for query expansion
_SYNONYMS = {
    "temperature": ["temp", "SST", "sea surface temperature", "water temperature"],
    "salinity": ["psal", "practical salinity", "salt content"],
    "oxygen": ["doxy", "dissolved oxygen", "DO"],
    "chlorophyll": ["chla", "chl-a", "chlorophyll-a", "phytoplankton"],
    "depth": ["pres", "pressure", "depth level"],
    "arabian sea": ["AS", "northwestern indian ocean", "lakshadweep sea"],
    "bay of bengal": ["BoB", "northeastern indian ocean"],
}


def expand_query(query: str) -> str:
    """Expand ocean synonyms in the query for better BM25 recall."""
    expanded = query
    for canonical, synonyms in _SYNONYMS.items():
        if canonical in query.lower():
            extra = ", ".join([s for s in synonyms if s.lower() not in query.lower()])
            if extra:
                expanded = str(expanded) + f" [{extra}]"
    return expanded
