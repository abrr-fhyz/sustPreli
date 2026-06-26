#!/usr/bin/env python3
"""Hit POST /analyze-ticket (and GET /health) with crafted inputs designed to
trigger each HTTP code documented in the README:

    200 — valid happy path
    400 — malformed JSON / missing required field / bad enum value
    422 — schema-valid but empty complaint
    500 — internal error (we cannot trigger without breaking the server, so
          this row is documented as 'not externally triggerable by design')

A 500 is documented but intentionally not user-triggerable per the safety
contract ("process never crashes on bad input"). We still log the attempt.
"""
import json
import sys
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
OUTPUT_FILE = Path("/home/shyan/Desktop/Code/sustPreli/http_code_test_results.json")

PASS, FAIL = "\033[92m✓\033[0m", "\033[91m✗\033[0m"
results = []


def hit(label: str, expect: int, **kw) -> dict:
    url = kw.pop("url", f"{BASE_URL}/analyze-ticket")
    try:
        r = requests.post(url, timeout=30, **kw) if "/analyze" in url \
            else requests.get(url, timeout=30, **kw)
    except Exception as exc:  # noqa: BLE001
        print(f"  {FAIL}  {label}: exception {exc}")
        return {"label": label, "expected": expect, "got": "exception", "ok": False, "error": str(exc)}

    ok = r.status_code == expect
    icon = PASS if ok else FAIL
    print(f"  {icon}  {label}: {r.status_code} (want {expect})")
    print(f"       body: {r.text[:200]}")
    return {
        "label": label,
        "expected": expect,
        "got": r.status_code,
        "ok": ok,
        "body": r.text[:300],
    }


print("\n=== HTTP code coverage ===\n")

# --- 200: valid happy path ---
results.append(hit(
    "200 valid happy path",
    200,
    json={
        "ticket_id": "T-HTTP-200",
        "complaint": "amar taka transfer hoy nai kintu kete nise",
        "transaction_history": [{
            "transaction_id": "TX-HTTP-200",
            "timestamp": "2026-01-01T10:00:00Z",
            "type": "transfer",
            "amount": 500,
            "counterparty": "01700000000",
            "status": "failed",
        }],
    },
))

# --- 200: health endpoint ---
results.append(hit(
    "200 GET /health",
    200,
    url=f"{BASE_URL}/health",
))

# --- 400: malformed JSON ---
results.append(hit(
    "400 malformed JSON (raw bytes, not parseable)",
    400,
    data=b"{this is not json",
    headers={"content-type": "application/json"},
))

# --- 400: missing required field (no complaint, no ticket_id) ---
results.append(hit(
    "400 missing required field (empty body)",
    400,
    json={},
))

# --- 400: missing only complaint (ticket_id present) ---
results.append(hit(
    "400 missing complaint field",
    400,
    json={"ticket_id": "T-MISSING"},
))

# --- 400: bad enum value (transaction.type) ---
results.append(hit(
    "400 bad enum on transaction.type",
    400,
    json={
        "ticket_id": "T-BAD-ENUM",
        "complaint": "something went wrong",
        "transaction_history": [{
            "transaction_id": "TX-BAD",
            "timestamp": "2026-01-01T10:00:00Z",
            "type": "teleport_the_money",   # not in allowed enum
            "amount": 100,
            "counterparty": "X",
            "status": "failed",
        }],
    },
))

# --- 400: bad enum on transaction.status ---
results.append(hit(
    "400 bad enum on transaction.status",
    400,
    json={
        "ticket_id": "T-BAD-STATUS",
        "complaint": "something went wrong",
        "transaction_history": [{
            "transaction_id": "TX-BAD2",
            "timestamp": "2026-01-01T10:00:00Z",
            "type": "transfer",
            "amount": 100,
            "counterparty": "X",
            "status": "maybe",
        }],
    },
))

# --- 400: wrong type (amount = string) ---
results.append(hit(
    "400 wrong type (amount is string, not number)",
    400,
    json={
        "ticket_id": "T-BAD-TYPE",
        "complaint": "test",
        "transaction_history": [{
            "transaction_id": "TX-BAD3",
            "timestamp": "2026-01-01T10:00:00Z",
            "type": "transfer",
            "amount": "five hundred",
            "counterparty": "X",
            "status": "failed",
        }],
    },
))

# --- 422: schema-valid but empty complaint (whitespace) ---
results.append(hit(
    "422 schema-valid but empty/whitespace complaint",
    422,
    json={"ticket_id": "T-EMPTY", "complaint": "   "},
))

# --- 422: schema-valid but empty complaint (empty string) ---
results.append(hit(
    "422 schema-valid but empty string complaint",
    422,
    json={"ticket_id": "T-EMPTY2", "complaint": ""},
))

# --- 500: not user-triggerable by design ---
# We add a marker row. The README and main.py both say the process never
# crashes — so this row documents the absence, not a real attempt.
print(f"  {PASS}  500 internal error: not externally triggerable (process never crashes by design; would require server fault injection)")
results.append({
    "label": "500 internal error",
    "expected": "not triggerable",
    "got": "not triggerable",
    "ok": True,
    "note": "main.py catches Exception globally; process never crashes on bad input per README contract",
})

# --- summary ---
print(f"\n=== Summary ===")
total = len([r for r in results if r["expected"] != "not triggerable"])
passed = sum(1 for r in results if r["ok"] and r["expected"] != "not triggerable")
print(f"{passed}/{total} triggered HTTP codes matched expectations")

OUTPUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False))
print(f"\nFull results → {OUTPUT_FILE}")
sys.exit(0 if passed == total else 1)