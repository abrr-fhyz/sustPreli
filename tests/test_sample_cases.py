"""The 10 public sample cases, wired as a reusable regression suite.

Source of truth: tests/sample_cases.json (a committed copy of the organizer's
SUST_Preli_Sample_Cases pack). Three tiers:

  A. Contract + safety  — every input -> 200, full schema, legal enums, safe
     reply. Deterministic, no key needed. THE hard must-pass gate.
  B. LLM routing        — functional equivalence vs expected_output, run against
     the real Gemini engine. Skipped unless GEMINI_API_KEY is set.
  C. Rules routing      — same functional check against the deterministic rules
     fallback. All 10 route correctly after the strategy tweaks (counterparty-
     frequency, fuzzy amount, ambiguity-guard).
"""
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import AnalyzeRequest
from app.services.evidence import ground_evidence, rules_verdict
from app.utils.safety import reply_violations

_DATA = json.loads((Path(__file__).parent / "sample_cases.json").read_text(encoding="utf-8"))
_META = _DATA["_meta"]
ALLOWED = _META["allowed_enums"]
REQUIRED = _META["schema_notes"]["output_required_fields"]
CASES = _DATA["cases"]
IDS = [c["id"] for c in CASES]

client = TestClient(app, raise_server_exceptions=False)

# Functional fields we compare for equivalence. severity + human_review_required
# are deterministic (rules / LLM-guard policy), so we assert them too.
_FUNCTIONAL = (
    "case_type", "department", "relevant_transaction_id", "evidence_verdict",
    "severity", "human_review_required",
)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_contract_and_safety(case):
    """Tier A — must pass for every case, with or without a key."""
    r = client.post("/analyze-ticket", json=case["input"])
    assert r.status_code == 200
    body = r.json()

    assert set(REQUIRED) <= set(body)
    assert body["ticket_id"] == case["input"]["ticket_id"]
    for field in ("evidence_verdict", "case_type", "severity", "department"):
        assert body[field] in ALLOWED[field], f"{field}={body[field]!r} not a legal enum"
    if body["relevant_transaction_id"] is not None:
        ids = {t["transaction_id"] for t in case["input"].get("transaction_history", [])}
        assert body["relevant_transaction_id"] in ids  # no hallucinated id
    assert reply_violations(body["customer_reply"]) == []  # outgoing reply is safe


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_rules_routing_matches_expected(case):
    """Tier C — deterministic rules fallback routes the samples correctly."""
    req = AnalyzeRequest(**case["input"])
    resp = rules_verdict(req, ground_evidence(req))
    exp = case["expected_output"]
    got = resp.model_dump()
    for field in _FUNCTIONAL:
        assert got[field] == exp[field], f"{case['id']} {field}: {got[field]!r} != {exp[field]!r}"


@pytest.mark.skipif(not os.getenv("RUN_LLM_TESTS"), reason="set RUN_LLM_TESTS=1 to hit live Gemini")
@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_llm_routing_matches_expected(case):
    """Tier B — the live Gemini engine reaches functional equivalence."""
    r = client.post("/analyze-ticket", json=case["input"])
    assert r.status_code == 200
    body = r.json()
    exp = case["expected_output"]
    for field in _FUNCTIONAL:
        assert body[field] == exp[field], f"{case['id']} {field}: {body[field]!r} != {exp[field]!r}"
