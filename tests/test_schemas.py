"""Schema contract: exact enums, required fields, request parsing."""
import pytest
from pydantic import ValidationError

from app.models.schemas import AnalyzeRequest, AnalyzeResponse


def test_request_requires_ticket_id_and_complaint():
    with pytest.raises(ValidationError):
        AnalyzeRequest(complaint="hi")  # missing ticket_id
    with pytest.raises(ValidationError):
        AnalyzeRequest(ticket_id="T1")  # missing complaint


def test_request_minimal_valid():
    r = AnalyzeRequest(ticket_id="T1", complaint="money gone")
    assert r.ticket_id == "T1"
    assert r.transaction_history == []  # defaults to empty, not None


def test_request_parses_transaction_history():
    r = AnalyzeRequest(
        ticket_id="T1",
        complaint="x",
        transaction_history=[
            {
                "transaction_id": "TX1",
                "timestamp": "2026-01-01T10:00:00Z",
                "type": "transfer",
                "amount": 500,
                "counterparty": "01700000000",
                "status": "completed",
            }
        ],
    )
    assert r.transaction_history[0].type == "transfer"
    assert r.transaction_history[0].status == "completed"


def test_request_rejects_bad_tx_type():
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            ticket_id="T1",
            complaint="x",
            transaction_history=[
                {
                    "transaction_id": "TX1",
                    "timestamp": "2026-01-01T10:00:00Z",
                    "type": "wormhole",  # invalid
                    "amount": 1,
                    "counterparty": "x",
                    "status": "completed",
                }
            ],
        )


def test_response_accepts_valid_enums():
    resp = AnalyzeResponse(
        ticket_id="T1",
        relevant_transaction_id=None,
        evidence_verdict="insufficient_data",
        case_type="other",
        severity="low",
        department="customer_support",
        agent_summary="s",
        recommended_next_action="a",
        customer_reply="r",
        human_review_required=False,
    )
    assert resp.evidence_verdict == "insufficient_data"


@pytest.mark.parametrize(
    "field,bad",
    [
        ("evidence_verdict", "consistant"),   # misspelled
        ("case_type", "wrong_transfers"),     # plural
        ("severity", "High"),                 # case
        ("department", "fraud"),              # variant
    ],
)
def test_response_rejects_enum_variants(field, bad):
    kwargs = dict(
        ticket_id="T1",
        relevant_transaction_id=None,
        evidence_verdict="consistent",
        case_type="other",
        severity="low",
        department="customer_support",
        agent_summary="s",
        recommended_next_action="a",
        customer_reply="r",
        human_review_required=False,
    )
    kwargs[field] = bad
    with pytest.raises(ValidationError):
        AnalyzeResponse(**kwargs)
