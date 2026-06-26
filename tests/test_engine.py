"""Engine orchestrator: investigate() returns a schema-valid, safe answer.

No GEMINI_API_KEY in the test env, so investigate() takes the deterministic
rules path. These pin the contract the route relies on: a complete, safe
AnalyzeResponse that echoes the ticket_id, and graceful behaviour on junk.
"""
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.engine import investigate
from app.utils.safety import scrub_response


def test_investigate_returns_response_echoing_ticket_id():
    req = AnalyzeRequest(ticket_id="T42", complaint="taka gone")
    resp = investigate(req)
    assert isinstance(resp, AnalyzeResponse)
    assert resp.ticket_id == "T42"


def test_investigate_vague_complaint_is_insufficient_and_safe():
    # No matchable detail -> do not guess, do not promise. Reply already safe.
    req = AnalyzeRequest(ticket_id="T1", complaint="something is wrong with my money")
    resp = investigate(req)
    assert resp.evidence_verdict == "insufficient_data"
    assert resp.case_type == "other"
    assert scrub_response(resp) == resp


def test_investigate_never_raises_on_weird_input():
    req = AnalyzeRequest(ticket_id="", complaint="")
    investigate(req)  # must not throw
