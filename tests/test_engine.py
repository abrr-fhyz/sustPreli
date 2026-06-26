"""Reasoning seam: investigate() returns a schema-valid, safe default.

Heuristics get filled in later — this only pins the contract the route
relies on: every call yields a complete AnalyzeResponse that echoes the
ticket_id and whose customer_reply passes the safety filter.
"""
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.engine import investigate
from app.utils.safety import scrub_response


def test_investigate_returns_response_echoing_ticket_id():
    req = AnalyzeRequest(ticket_id="T42", complaint="taka gone")
    resp = investigate(req)
    assert isinstance(resp, AnalyzeResponse)
    assert resp.ticket_id == "T42"


def test_investigate_default_is_safe_and_escalates_when_unsure():
    # No transaction_history -> cannot verify -> insufficient_data + escalate.
    req = AnalyzeRequest(ticket_id="T1", complaint="???")
    resp = investigate(req)
    assert resp.evidence_verdict == "insufficient_data"
    assert resp.human_review_required is True
    # default reply must already be safe (no scrub change needed)
    assert scrub_response(resp) == resp


def test_investigate_never_raises_on_weird_input():
    req = AnalyzeRequest(ticket_id="", complaint="")
    investigate(req)  # must not throw
