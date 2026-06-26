"""Outgoing-reply safety net (field-level rules from the rubric).

These run on the RESPONSE we are about to send, not the user's complaint.
Penalties guarded: credential ask (-15), unauthorized money promise (-10),
suspicious 3rd-party referral (-10).
"""
from app.models.schemas import AnalyzeResponse
from app.utils.safety import reply_violations, scrub_response


def _resp(reply="We are reviewing your case.", action="Forward to ops team."):
    return AnalyzeResponse(
        ticket_id="T1",
        relevant_transaction_id=None,
        evidence_verdict="insufficient_data",
        case_type="other",
        severity="low",
        department="customer_support",
        agent_summary="s",
        recommended_next_action=action,
        customer_reply=reply,
        human_review_required=False,
    )


def test_detects_credential_request():
    assert "credential_request" in reply_violations("Please share your OTP to verify.")
    assert "credential_request" in reply_violations("Tell me your PIN and password.")
    assert "credential_request" in reply_violations("Confirm your full card number.")


def test_detects_unauthorized_promise():
    assert "unauthorized_promise" in reply_violations("We will refund you 500 BDT now.")
    assert "unauthorized_promise" in reply_violations("Your account will be unblocked today.")


def test_detects_third_party_referral():
    assert "third_party_referral" in reply_violations("Message us on WhatsApp at this link http://bit.ly/x")


def test_safe_text_has_no_violations():
    assert reply_violations("Any eligible amount will be returned through official channels.") == []


def test_scrub_replaces_credential_ask_in_reply():
    bad = _resp(reply="To help, send your OTP and password.")
    cleaned = scrub_response(bad)
    assert reply_violations(cleaned.customer_reply) == []
    assert cleaned.ticket_id == "T1"  # other fields untouched


def test_scrub_softens_unauthorized_promise_in_action():
    bad = _resp(action="We will refund the customer immediately.")
    cleaned = scrub_response(bad)
    assert reply_violations(cleaned.recommended_next_action) == []


def test_scrub_leaves_safe_response_unchanged():
    ok = _resp()
    assert scrub_response(ok) == ok
