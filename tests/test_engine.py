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


def test_llm_guard_overrides_severity_review_and_duplicate_id():
    """The rules-guard must correct the LLM's deterministic fields: over-eager
    escalation, severity drift, and picking the wrong duplicate charge."""
    from app.services.evidence import EvidenceFacts
    from app.services.llm import TriageAnalysis, _to_response

    # LLM picks the FIRST charge + medium + review False; facts say the later one.
    ta = TriageAnalysis(
        relevant_transaction_id="TXN-1", evidence_verdict="consistent",
        case_type="duplicate_payment", severity="medium", department="payments_ops",
        agent_summary="s", recommended_next_action="a", customer_reply="r",
        human_review_required=False, confidence=0.5, reason_codes=[],
    )
    facts = EvidenceFacts(
        candidate_tx_ids=["TXN-1", "TXN-2"], suspected_duplicate_id="TXN-2",
        ambiguous=True, no_history=False, hints={}, amounts=[850.0],
        counterparty_repeat=False, injection=False,
    )
    req = AnalyzeRequest(
        ticket_id="T", complaint="charged twice",
        transaction_history=[
            {"transaction_id": "TXN-1", "timestamp": "2026-04-14T08:15:30Z",
             "type": "payment", "amount": 850, "counterparty": "B", "status": "completed"},
            {"transaction_id": "TXN-2", "timestamp": "2026-04-14T08:15:42Z",
             "type": "payment", "amount": 850, "counterparty": "B", "status": "completed"},
        ],
    )
    out = _to_response(req, ta, facts)
    assert out.relevant_transaction_id == "TXN-2"   # later duplicate, not LLM's TXN-1
    assert out.severity == "high"                   # policy, not LLM's medium
    assert out.human_review_required is True         # policy, not LLM's False
