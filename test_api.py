#!/usr/bin/env python3
"""
API Test Script — offline (local) and online (Render)
Usage:
  python test_api.py          # tests localhost by default
  python test_api.py online   # tests your Render URL
"""

import sys
import requests

# ── CONFIG ────────────────────────────────────────────────────────────────────
LOCAL_URL  = "http://localhost:8000"
REMOTE_URL = "https://YOUR-APP.onrender.com"  # <- replace this
# ─────────────────────────────────────────────────────────────────────────────

mode     = sys.argv[1] if len(sys.argv) > 1 else "offline"
BASE_URL = REMOTE_URL if mode == "online" else LOCAL_URL

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"


def test(label, method, path, **kwargs):
    url = BASE_URL + path
    try:
        resp = requests.request(method, url, timeout=15, **kwargs)
        ok   = resp.status_code < 400
        icon = PASS if ok else FAIL
        print(f"  {icon}  {label}")
        print(f"       {method} {url}  →  {resp.status_code}")
        print(f"       {resp.json()}\n")
    except requests.exceptions.ConnectionError:
        print(f"  {FAIL}  {label}")
        print(f"       Could not connect to {url}")
        print(f"       (is the server running?)\n")
    except Exception as e:
        print(f"  {FAIL}  {label}  —  {e}\n")


print(f"\n{'='*50}")
print(f"  Mode : {'ONLINE  (' + REMOTE_URL + ')' if mode == 'online' else 'OFFLINE (' + LOCAL_URL + ')'}")
print(f"{'='*50}\n")

# ── TESTS ─────────────────────────────────────────────────────────────────────

test("Health check",
     "GET", "/health")

test("Analyze — normal input",
     "POST", "/analyze",
     json={"input": "hello world"})

test("Analyze — empty input",
     "POST", "/analyze",
     json={"input": ""})

test("Analyze — blocked keyword (should return 400)",
     "POST", "/analyze",
     json={"input": "my password is 1234"})

test("Analyze — missing field (should return 422)",
     "POST", "/analyze",
     json={})

test("404 route",
     "GET", "/nonexistent")