import asyncio
import httpx
import json
import time
import random
from typing import List, Dict, Any

# ── Configuration ────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
SESSION_ID = f"test_session_{int(time.time())}"

QUERIES = [
    # ── 1) NEAREST_FLOAT (Spatial Queries) ───────────────────────────────────
    "Find the 5 closest floats to Mumbai.",
    "Show me the nearest ARGO float to the Maldives.",
    "Which float is closest to Lakshadweep islands?",
    "Where is the nearest float to Chennai right now?",
    "Find ocean data near Mumbai for the last 30 days.",
    
    # ── 2) ANALYTICAL (SQL-heavy) ──────────────────────────────────────────
    "What is the average surface temperature in the Arabian Sea?",
    "Show me the max salinity in the Bay of Bengal for the last 6 months.",
    "How many observations do we have in the Indian Ocean this year?",
    "Average oxygen levels in the Equatorial Indian Ocean top 100m.",
    "Compare salinity between the Arabian Sea and Bay of Bengal.",
    
    # ── 3) MULTI_HOP (Decomposition) ─────────────────────────────────────────
    "Find the nearest float to Goa and show me the average temp in Arabian Sea.",
    "Compare Bay of Bengal vs Arabian Sea pressure and locate nearest float to Mumbai.",
    "Is it saltier in the Bay of Bengal or Arabian Sea? Also where is float 2902093?",
    
    # ── 4) KNOWLEDGE GRAPH (Context Enrichment) ─────────────────────────────
    "How does salinity relate to ocean currents in the Indian Ocean?",
    "Explain the role of ARGO floats in monitoring climate change.",
    "What are the main variables tracked by BGC-Argo floats?",
    "How is post-monsoon upwelling reflected in chlorophyll data?",
    
    # ── 5) PERSONALIZATION ──────────────────────────────────────────────────
    "Set my preferred region to 'Arabian Sea' and variables to 'temp, psal'.",
    "What are my current preferences?",
    "Based on my regions, show me the latest data.",
    
    # ── 6) TRAJECTORY & PROFILE ─────────────────────────────────────────────
    "Show the trajectory for float 6902737.",
    "Get the depth profile for float 2902130 cycle 45.",
    
    # ── 7) EDGE CASES & RETRY ────────────────────────────────────────────────
    "Retry that last one but only for surface data.",
    "What is the deepest observation we have?",
    "Ocean data for 12.5 N, 72.8 E.",
    "Hello! How are you today? (General conversation)",
]

# ── Stress Testing Engine ─────────────────────────────────────────────────────
async def run_query(client: httpx.AsyncClient, q: str):
    print(f"\n[QUERY] -> {q}")
    start = time.perf_counter()
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/chat",
            json={"question": q, "session": SESSION_ID},
            timeout=60.0
        )
        duration = time.perf_counter() - start
        if response.status_code == 200:
            data = response.json()
            intent = data.get("intent", "UNKNOWN")
            ans_len = len(data.get("answer_markdown", ""))
            print(f"[{intent}] ✅ Success ({duration:.2f}s) | Answer: {ans_len} chars")
            if data.get("trace_id"):
                print(f"      Trace: {BASE_URL}/debug?trace_id={data['trace_id']}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"💥 Exception: {e}")

async def main():
    print(f"🚀 Starting OceanMind Stress Test Suite")
    print(f"📂 Session: {SESSION_ID}")
    print(f"⚡ Testing {len(QUERIES)} unique queries across all intents")
    
    async with httpx.AsyncClient() as client:
        for q in QUERIES:
            await run_query(client, q)
            # Subtle delay to allow backend to breathe
            await asyncio.sleep(0.5)

    print("\n" + "="*50)
    print("🎯 Stress Test Complete!")
    print(f"Check backend logs for Detailed Pipeline spans.")

if __name__ == "__main__":
    asyncio.run(main())
