#!/usr/bin/env python3
"""Manual smoke test (not pytest). Hits a running server.

  python smoke.py            # localhost:8000
  python smoke.py online     # the REMOTE_URL below
"""
import sys

import requests

LOCAL_URL = "http://localhost:8000"
REMOTE_URL = "https://sustpreli.onrender.com"  # <- replace after deploy

mode = sys.argv[1] if len(sys.argv) > 1 else "offline"
BASE = REMOTE_URL if mode == "online" else LOCAL_URL

PASS, FAIL = "\033[92m✓\033[0m", "\033[91m✗\033[0m"


def check(label, method, path, expect, **kw):
    try:
        r = requests.request(method, BASE + path, timeout=30, **kw)
        ok = r.status_code == expect
        print(f"  {PASS if ok else FAIL}  {label}: {r.status_code} (want {expect})")
        print(f"       {r.text[:200]}\n")
    except Exception as e:  # noqa: BLE001
        print(f"  {FAIL}  {label}: {e}\n")


VALID = {
    "ticket_id": "T1",
    "complaint": "amar taka transfer hoy nai kintu kete nise",
    "transaction_history": [
        {
            "transaction_id": "TX1",
            "timestamp": "2026-01-01T10:00:00Z",
            "type": "transfer",
            "amount": 500,
            "counterparty": "01700000000",
            "status": "failed",
        }
    ],
}

print(f"\n{'='*50}\n  {BASE}\n{'='*50}\n")
check("health", "GET", "/health", 200)
check("valid ticket", "POST", "/analyze-ticket", 200, json=VALID)
check("missing complaint -> 400", "POST", "/analyze-ticket", 400, json={"ticket_id": "T1"})
check("empty complaint -> 422", "POST", "/analyze-ticket", 422, json={"ticket_id": "T1", "complaint": "  "})
check("bad json -> 400", "POST", "/analyze-ticket", 400, data=b"{nope", headers={"content-type": "application/json"})
