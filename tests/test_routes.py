"""HTTP contract for /health and /analyze-ticket.

Code map (spec): 200 ok · 400 malformed (bad JSON / missing required / bad enum)
· 422 schema-valid-but-semantically-invalid (empty complaint) · 500 internal
(non-sensitive). The process must never crash — every input yields a response.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

# raise_server_exceptions=False -> client returns the 500 the real server sends
# instead of re-raising, so we can assert on the safe error body.
client = TestClient(app, raise_server_exceptions=False)

VALID = {
    "ticket_id": "T1",
    "complaint": "amar taka transfer hoy nai",
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

RESPONSE_KEYS = {
    "ticket_id", "relevant_transaction_id", "evidence_verdict", "case_type",
    "severity", "department", "agent_summary", "recommended_next_action",
    "customer_reply", "human_review_required",
}


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyze_valid_returns_200_and_full_schema():
    r = client.post("/analyze-ticket", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert RESPONSE_KEYS <= set(body)
    assert body["ticket_id"] == "T1"


def test_missing_required_field_is_400():
    r = client.post("/analyze-ticket", json={"ticket_id": "T1"})  # no complaint
    assert r.status_code == 400


def test_invalid_json_is_400():
    r = client.post(
        "/analyze-ticket",
        content=b"{not json",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400


def test_bad_enum_is_400():
    bad = {**VALID, "transaction_history": [{**VALID["transaction_history"][0], "type": "wormhole"}]}
    r = client.post("/analyze-ticket", json=bad)
    assert r.status_code == 400


def test_empty_complaint_is_422():
    r = client.post("/analyze-ticket", json={"ticket_id": "T1", "complaint": "   "})
    assert r.status_code == 422


def test_internal_error_is_500_without_leaking(monkeypatch):
    def boom(_req):
        raise RuntimeError("db password=hunter2 secret stack detail")

    monkeypatch.setattr("app.routes.analyze.investigate", boom)
    r = client.post("/analyze-ticket", json=VALID)
    assert r.status_code == 500
    assert "hunter2" not in r.text and "password" not in r.text.lower()


def test_response_is_always_safe_even_if_engine_unsafe(monkeypatch):
    from app.models.schemas import AnalyzeResponse

    def leaky(req):
        return AnalyzeResponse(
            ticket_id=req.ticket_id,
            relevant_transaction_id=None,
            evidence_verdict="insufficient_data",
            case_type="other",
            severity="low",
            department="customer_support",
            agent_summary="s",
            recommended_next_action="We will refund you now.",
            customer_reply="Please send your OTP to verify.",
            human_review_required=False,
        )

    monkeypatch.setattr("app.routes.analyze.investigate", leaky)
    r = client.post("/analyze-ticket", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert "otp" not in body["customer_reply"].lower()
