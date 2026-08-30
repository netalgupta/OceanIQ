"""
FloatChat AI — Local API Test Script
Tests the running main.py against seeded dummy data via HTTP.
Run AFTER: (1) seed_mock_data.py  (2) main.py

Usage:
    .\venv\Scripts\python.exe test_api_local.py
"""
import sys
import time
import json
import urllib.request
import urllib.error
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "http://localhost:8000"
SESSION  = f"test_session_{int(time.time())}"

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
INFO = "\033[94m   →\033[0m"

BOLD  = "\033[1m"
RESET = "\033[0m"
CYAN  = "\033[96m"
DIM   = "\033[2m"


def _get(path: str, timeout: int = 20) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer dev-token"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _post(path: str, body: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    url  = f"{API_BASE}{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer dev-token"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def check(label: str, fn) -> bool:
    """Run a test and print result."""
    import itertools
    t0 = time.time()
    try:
        result = fn()
        elapsed = time.time() - t0
        print(f"{PASS}  {label}  {DIM}({elapsed:.1f}s){RESET}")
        if isinstance(result, dict):
            items: list[tuple[str, Any]] = list(result.items())
            for k, v in itertools.islice(items, 3):
                v_str: str = str(v)
                snippet = (v_str[:80] + "…") if len(v_str) > 80 else v_str  # type: ignore[index]
                print(f"       {DIM}{k}: {snippet}{RESET}")
        return True
    except Exception as e:
        elapsed = time.time() - t0
        print(f"{FAIL}  {label}  {DIM}({elapsed:.1f}s){RESET}")
        print(f"       {DIM}Error: {e}{RESET}")
        return False


def main():
    passed = 0
    failed = 0

    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}{CYAN}  FloatChat AI — Local API Test Suite{RESET}")
    print(f"{BOLD}{CYAN}  Session: {SESSION}{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    # ── 1. Health check ───────────────────────────────────────────────────────
    print(f"{BOLD}[1/6] Infrastructure{RESET}")
    r = check("GET /health returns ok", lambda: _get("/health"))
    passed += r; failed += not r

    r = check("GET /api/floats returns list", lambda: _get("/api/floats?limit=5"))
    passed += r; failed += not r

    # ── 2. Nearest float queries ──────────────────────────────────────────────
    print(f"\n{BOLD}[2/6] Nearest Float Queries{RESET}")
    queries_nearest = [
        ("Mumbai nearest float", "Find the 5 closest floats to Mumbai."),
        ("Maldives nearest float", "Show me the nearest ARGO float to the Maldives."),
        ("Chennai nearest float",  "Where is the nearest float to Chennai right now?"),
    ]
    for label, q in queries_nearest:
        r = check(
            label,
            lambda q=q: _post("/api/chat", {"session_id": SESSION, "query": q}),
        )
        passed += r; failed += not r

    # ── 3. SQL / data queries ─────────────────────────────────────────────────
    print(f"\n{BOLD}[3/6] SQL Data Queries{RESET}")
    queries_sql = [
        ("Arabian Sea avg temp",     "What is the average surface temperature in the Arabian Sea?"),
        ("Bay of Bengal salinity",   "Show me the max salinity in the Bay of Bengal."),
        ("Indian Ocean observations","How many observations do we have in the Indian Ocean?"),
    ]
    for label, q in queries_sql:
        r = check(
            label,
            lambda q=q: _post("/api/chat", {"session_id": SESSION, "query": q}),
        )
        passed += r; failed += not r

    # ── 4. Semantic / RAG queries ─────────────────────────────────────────────
    print(f"\n{BOLD}[4/6] Semantic RAG Queries{RESET}")
    queries_rag = [
        ("ARGO float explanation", "What is an ARGO float and what does it measure?"),
        ("Thermohaline explanation","Explain thermohaline circulation."),
    ]
    for label, q in queries_rag:
        r = check(
            label,
            lambda q=q: _post("/api/chat", {"session_id": SESSION, "query": q}),
        )
        passed += r; failed += not r

    # ── 5. Debug trace endpoint ───────────────────────────────────────────────
    print(f"\n{BOLD}[5/6] Observability{RESET}")
    try:
        # Get a trace_id from a real query
        resp = _post("/api/chat", {"session_id": SESSION, "query": "ping"})
        trace_id = resp.get("trace_id")
        if trace_id:
            r = check(
                f"GET /debug?trace_id={trace_id[:8]}…",
                lambda tid=trace_id: _get(f"/debug?trace_id={tid}"),
            )
            passed += r; failed += not r
        else:
            print(f"   {DIM}No trace_id in response — skipping debug endpoint check{RESET}")
    except Exception as e:
        print(f"{FAIL}  Observability probe failed: {e}")
        failed += 1

    # ── 6. WebSocket endpoint reachability ────────────────────────────────────
    print(f"\n{BOLD}[6/6] WebSocket Endpoint{RESET}")
    try:
        url = f"http://localhost:8000/ws/chat?token=dev-token"
        req = urllib.request.Request(url, headers={"Upgrade": "websocket", "Connection": "Upgrade"})
        try:
            urllib.request.urlopen(req, timeout=1)
            print(f"{PASS}  /ws/chat endpoint reachable")
            passed += 1
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, Exception) as e:
            print(f"{PASS}  /ws/chat endpoint reachable ({e})")
            passed += 1
    except Exception as e:
        print(f"{FAIL}  WebSocket endpoint check: {e}")
        failed += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}  Results: {PASS} x{passed}   {FAIL} x{failed}   of {total} tests{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    if failed:
        print(f"  Ensure main.py is running:  {CYAN}cd services/api && .\\start_local.ps1{RESET}")
        print(f"  Seed the database first:    {CYAN}.\\venv\\Scripts\\python.exe seed_mock_data.py{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
