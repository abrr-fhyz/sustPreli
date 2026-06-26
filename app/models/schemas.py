"""QueueStorm Investigator request/response contract.

Enums must match the spec EXACTLY — case/plural/spelling variants are
schema violations (15% of score). Literal types enforce this at parse time.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ── enum aliases ──────────────────────────────────────────────────────────────
Language = Literal["en", "bn", "mixed"]
Channel = Literal["in_app_chat", "call_center", "email", "merchant_portal", "field_agent"]
UserType = Literal["customer", "merchant", "agent", "unknown"]
TxType = Literal["transfer", "payment", "cash_in", "cash_out", "settlement", "refund"]
TxStatus = Literal["completed", "failed", "pending", "reversed"]

EvidenceVerdict = Literal["consistent", "inconsistent", "insufficient_data"]
CaseType = Literal[
    "wrong_transfer",
    "payment_failed",
    "refund_request",
    "duplicate_payment",
    "merchant_settlement_delay",
    "agent_cash_in_issue",
    "phishing_or_social_engineering",
    "other",
]
Severity = Literal["low", "medium", "high", "critical"]
Department = Literal[
    "customer_support",
    "dispute_resolution",
    "payments_ops",
    "merchant_operations",
    "agent_operations",
    "fraud_risk",
]


# ── request ───────────────────────────────────────────────────────────────────
class TransactionEntry(BaseModel):
    transaction_id: str
    timestamp: str  # ISO8601; kept as str — we never trust/parse beyond compare
    type: TxType
    amount: float
    counterparty: str
    status: TxStatus

    @field_validator("amount", mode="before")
    @classmethod
    def _amount_must_be_number(cls, v):
        # spec §5.2: amount is a number. Reject strings ("100") and bools — pydantic
        # would otherwise coerce them. int/float pass through.
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("amount must be a number")
        return v


class AnalyzeRequest(BaseModel):
    ticket_id: str
    complaint: str
    language: Optional[Language] = None
    channel: Optional[Channel] = None
    user_type: Optional[UserType] = None
    campaign_context: Optional[str] = None
    transaction_history: list[TransactionEntry] = Field(default_factory=list)
    metadata: Optional[dict] = None

    @field_validator("transaction_history")
    @classmethod
    def _cap_history(cls, v):
        # ponytail: bound LLM token cost on adversarial oversized payloads. Brief
        # says history is "typically 2 to 5"; 100 is generous. Keep the most recent
        # by timestamp so the relevant transaction survives the cap.
        if len(v) > 100:
            return sorted(v, key=lambda t: t.timestamp, reverse=True)[:100]
        return v


# ── response ──────────────────────────────────────────────────────────────────
class AnalyzeResponse(BaseModel):
    ticket_id: str
    relevant_transaction_id: Optional[str]
    evidence_verdict: EvidenceVerdict
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    human_review_required: bool
    confidence: Optional[float] = None
    reason_codes: Optional[list[str]] = None
