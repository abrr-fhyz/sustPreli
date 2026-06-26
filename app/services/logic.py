from app.models.schemas import AnalyzeRequest


def run_analysis(request: AnalyzeRequest) -> dict:
    complaint = request.complaint.lower()
    transactions = request.transaction_history or []

    # Default response
    response = {
        "ticket_id": request.ticket_id,
        "relevant_transaction_id": None,
        "evidence_verdict": "insufficient_data",
        "case_type": "other",
        "severity": "low",
        "department": "customer_support",
        "agent_summary": "Unable to determine the exact issue from the complaint.",
        "recommended_next_action": (
            "Ask the customer for more information."
        ),
        "customer_reply": (
            "Thank you for contacting us. Please provide "
            "additional details about the issue. "
            "Please do not share your PIN or OTP with anyone."
        ),
        "human_review_required": False,
        "confidence": 0.5,
        "reason_codes": ["needs_clarification"]
    }

    # -------------------------------------------------
    # PHISHING / SOCIAL ENGINEERING
    # -------------------------------------------------
    phishing_keywords = [
        "otp",
        "pin",
        "password",
        "called me",
        "account blocked",
        "share code"
    ]

    if any(k in complaint for k in phishing_keywords):
        response.update({
            "case_type": "phishing_or_social_engineering",
            "severity": "critical",
            "department": "fraud_risk",
            "agent_summary": (
                "Customer reports a possible phishing or "
                "social engineering attempt."
            ),
            "recommended_next_action": (
                "Escalate immediately to fraud risk team."
            ),
            "customer_reply": (
                "We never ask for your PIN, OTP, or password. "
                "Please do not share these with anyone. "
                "Our fraud team has been notified."
            ),
            "human_review_required": True,
            "confidence": 0.95,
            "reason_codes": ["phishing"]
        })

        return response

    # -------------------------------------------------
    # WRONG TRANSFER
    # -------------------------------------------------
    if "wrong" in complaint and (
        "transfer" in complaint or "sent" in complaint
    ):

        txn = next(
            (t for t in transactions if t.type == "transfer"),
            None
        )

        if txn:
            response.update({
                "relevant_transaction_id": txn.transaction_id,
                "evidence_verdict": "consistent",
                "case_type": "wrong_transfer",
                "severity": "high",
                "department": "dispute_resolution",
                "agent_summary": (
                    f"Customer claims transfer "
                    f"{txn.transaction_id} was sent to "
                    f"the wrong recipient."
                ),
                "recommended_next_action": (
                    "Initiate wrong transfer dispute workflow."
                ),
                "customer_reply": (
                    f"We have noted your concern regarding "
                    f"transaction {txn.transaction_id}. "
                    "Our dispute team will review the case. "
                    "Please do not share your PIN or OTP."
                ),
                "human_review_required": True,
                "confidence": 0.9,
                "reason_codes": [
                    "wrong_transfer",
                    "transaction_match"
                ]
            })

        return response

    # -------------------------------------------------
    # PAYMENT FAILED
    # -------------------------------------------------
    if "failed" in complaint or "deducted" in complaint:

        txn = next(
            (t for t in transactions if t.status == "failed"),
            None
        )

        if txn:
            response.update({
                "relevant_transaction_id": txn.transaction_id,
                "evidence_verdict": "consistent",
                "case_type": "payment_failed",
                "severity": "high",
                "department": "payments_ops",
                "agent_summary": (
                    f"Customer reports failed payment "
                    f"{txn.transaction_id} with possible "
                    "balance deduction."
                ),
                "recommended_next_action": (
                    "Investigate payment ledger and reversal."
                ),
                "customer_reply": (
                    f"We have noted the issue with "
                    f"{txn.transaction_id}. "
                    "Our payments team will investigate and "
                    "any eligible amount will be returned "
                    "through official channels. "
                    "Please do not share your PIN or OTP."
                ),
                "human_review_required": False,
                "confidence": 0.9,
                "reason_codes": ["payment_failed"]
            })

        return response

    # -------------------------------------------------
    # REFUND REQUEST
    # -------------------------------------------------
    if "refund" in complaint:

        txn = transactions[0] if transactions else None

        response.update({
            "relevant_transaction_id":
                txn.transaction_id if txn else None,
            "evidence_verdict":
                "consistent" if txn else "insufficient_data",
            "case_type": "refund_request",
            "severity": "low",
            "department": "customer_support",
            "agent_summary":
                "Customer requested a refund.",
            "recommended_next_action":
                "Inform customer about refund policy.",
            "customer_reply": (
                "Refund eligibility depends on policy review. "
                "Any eligible amount will be returned through "
                "official channels. Please do not share your "
                "PIN or OTP."
            ),
            "human_review_required": False,
            "confidence": 0.8,
            "reason_codes": ["refund_request"]
        })

        return response

    # -------------------------------------------------
    # MERCHANT SETTLEMENT
    # -------------------------------------------------
    if "settlement" in complaint:

        txn = next(
            (t for t in transactions if t.type == "settlement"),
            None
        )

        if txn:
            response.update({
                "relevant_transaction_id": txn.transaction_id,
                "evidence_verdict": "consistent",
                "case_type": "merchant_settlement_delay",
                "severity": "medium",
                "department": "merchant_operations",
                "agent_summary":
                    "Merchant settlement delay reported.",
                "recommended_next_action":
                    "Verify settlement batch status.",
                "customer_reply": (
                    f"We have noted your concern regarding "
                    f"{txn.transaction_id}. "
                    "Our merchant operations team will review "
                    "the settlement status."
                ),
                "human_review_required": False,
                "confidence": 0.9,
                "reason_codes": ["merchant_settlement"]
            })

        return response

    # -------------------------------------------------
    # AGENT CASH IN
    # -------------------------------------------------
    if (
        "cash in" in complaint
        or "ক্যাশ ইন" in request.complaint
    ):

        txn = next(
            (t for t in transactions if t.type == "cash_in"),
            None
        )

        if txn:
            response.update({
                "relevant_transaction_id": txn.transaction_id,
                "evidence_verdict": "consistent",
                "case_type": "agent_cash_in_issue",
                "severity": "high",
                "department": "agent_operations",
                "agent_summary":
                    "Customer reports cash-in issue.",
                "recommended_next_action":
                    "Investigate agent transaction.",
                "customer_reply": (
                    f"Transaction {txn.transaction_id} "
                    "will be reviewed by our operations team. "
                    "Please do not share your PIN or OTP."
                ),
                "human_review_required": True,
                "confidence": 0.88,
                "reason_codes": ["cash_in_issue"]
            })

        return response

    return response