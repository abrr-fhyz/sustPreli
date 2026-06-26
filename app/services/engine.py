"""Reasoning seam — the investigator.

This is where the heuristic / hybrid logic plugs in later (engine choice TBD).
For now it returns a SAFE, schema-valid default: when we cannot verify a
complaint against transaction_history we say so (insufficient_data) and escalate
to a human rather than guess. Never raises — the route depends on that.
"""
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.utils.safety import SAFE_ACTION, SAFE_REPLY


def investigate(req: AnalyzeRequest) -> AnalyzeResponse:
    # TODO(heuristics): inspect req.transaction_history vs req.complaint to set
    # relevant_transaction_id, evidence_verdict, case_type, department, severity.
    return AnalyzeResponse(
        ticket_id=req.ticket_id,
        relevant_transaction_id=None,
        evidence_verdict="insufficient_data",
        case_type="other",
        severity="low",
        department="customer_support",
        agent_summary="Complaint received; not yet verifiable against the provided transaction history.",
        recommended_next_action=SAFE_ACTION,
        customer_reply=SAFE_REPLY,
        human_review_required=True,  # safe default: escalate when unsure
        confidence=0.0,
        reason_codes=["default_unverified"],
    )
