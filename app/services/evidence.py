"""Deterministic evidence pre-pass — the rules that ground the LLM.

Pure, no I/O, never raises. Scans the complaint + transaction_history and
produces hard, auditable facts (candidate transactions, duplicate suspicion,
ambiguity, keyword hints). The LLM reasons over these facts; when the LLM is
unavailable, `rules_verdict` turns the same facts into a safe routed answer.

Baseline matcher = exact-ish amount match + ambiguity + duplicate detection.
Smarter scoring (time-decay match, fuzzy amounts, counterparty-frequency scam
detection) is the next strategy phase — see memory `queuestorm-next-tweaks`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schemas import AnalyzeRequest, AnalyzeResponse, TransactionEntry

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# en + bn + banglish keyword tables. Hints only — the LLM / rules_verdict decide.
_KW: dict[str, list[str]] = {
    "phishing": [
        "otp", "pin", "password", "cvv", "scam", "phishing", "fraud",
        "blocked", "block", "suspicious", "verify", "verification",
        "called me", "someone called", "they called", "phone call",
        "ওটিপি", "পিন", "পাসওয়ার্ড", "প্রতারণা", "ব্লক", "কল",
    ],
    "duplicate": [
        "twice", "two times", "double", "duplicate", "deducted twice",
        "charged twice", "দুইবার", "দুবার", "ডাবল",
    ],
    "wrong_transfer": [
        "wrong number", "wrong person", "wrong recipient", "wrong account",
        "mistakenly", "by mistake", "unknown person", "unknown number",
        "didn't get", "didn't receive", "did not receive", "not received",
        "hasn't received", "haven't received", "reverse it", "reverse the",
        "ভুল", "পাইনি", "পায়নি",
    ],
    "settlement": [
        "settle", "settlement", "batch", "payout", "sales", "merchant",
        "সেটেলমেন্ট", "নিষ্পত্তি",
    ],
    "cash_in": ["cash in", "cash-in", "cashin", "ক্যাশ ইন", "ক্যাশইন", "এজেন্ট"],
    "payment_failed": ["failed", "fail", "unsuccessful", "declined", "ব্যর্থ"],
    "refund": [
        "refund", "money back", "changed my mind", "want it back", "return it",
        "ফেরত", "রিফান্ড",
    ],
}

# Authority-spoofing / prompt-injection markers. Never legitimate in a real
# complaint -> always escalate + neutralise the reply (no echo of injected text).
_INJECTION = [
    "authorization code", "auth code", "authorisation code",
    "ignore previous", "ignore all", "ignore the above", "disregard previous",
    "disregard all", "system prompt", "reveal your prompt", "developer mode",
    "admin override", "system override", "pre-authorized", "pre authorized",
    "preauthorized", "agent says", "staff msg", "support agent msg",
    "this is support", "this is bkash", "this is the admin", "i am from bkash",
    "i am support", "i am an admin", "as an admin", "override the",
]


def _has(text: str, keywords: list[str]) -> bool:
    for k in keywords:
        # word-boundary for short ascii tokens (avoid "pin" inside "shopping");
        # substring for phrases and non-ascii (Bangla) where \b is unreliable.
        if " " in k or not k.isascii():
            if k in text:
                return True
        elif re.search(r"\b" + re.escape(k) + r"\b", text):
            return True
    return False


def _amounts(text: str) -> set[float]:
    t = text.translate(_BN_DIGITS)
    out: set[float] = set()
    for m in re.findall(r"\d[\d,]*(?:\.\d+)?", t):
        try:
            out.add(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def _amt_match(actual: float, claimed: float) -> bool:
    # fuzzy: humans round (500 vs 495.6). Tolerance = 2% of claimed, floor 1.0.
    # ponytail: flat tolerance; widen if real data shows bigger rounding gaps.
    return abs(actual - claimed) <= max(1.0, 0.02 * claimed)


def _first(hist: list[TransactionEntry], **match) -> TransactionEntry | None:
    for t in hist:
        if all(getattr(t, k) == v for k, v in match.items()):
            return t
    return None


@dataclass
class EvidenceFacts:
    candidate_tx_ids: list[str]
    suspected_duplicate_id: str | None
    ambiguous: bool
    no_history: bool
    hints: dict[str, bool]
    amounts: list[float]
    # a matched payee the user transacts with repeatedly (>=3x) — a habitual
    # recipient contradicts an "accidental/wrong transfer" claim.
    counterparty_repeat: bool
    # complaint carries authority-spoofing / prompt-injection markers.
    injection: bool


def ground_evidence(req: AnalyzeRequest) -> EvidenceFacts:
    c = req.complaint.lower()
    amts = _amounts(req.complaint)
    hist = req.transaction_history

    candidates = [t for t in hist if any(_amt_match(t.amount, a) for a in amts)]

    # counterparty frequency: does any matched payee appear >=3x in history?
    repeat = False
    cp_counts: dict[str, int] = {}
    for t in hist:
        cp_counts[t.counterparty] = cp_counts.get(t.counterparty, 0) + 1
    for t in candidates:
        if cp_counts.get(t.counterparty, 0) >= 3:
            repeat = True
            break

    # duplicate: >=2 completed payments of identical amount -> suspect the later.
    # ISO8601 'Z' timestamps sort correctly lexically, so max() picks latest.
    dup_id: str | None = None
    by_amount: dict[float, list[TransactionEntry]] = {}
    for t in hist:
        if t.type == "payment" and t.status == "completed":
            by_amount.setdefault(t.amount, []).append(t)
    for group in by_amount.values():
        if len(group) >= 2:
            dup_id = max(group, key=lambda t: t.timestamp).transaction_id
            break

    return EvidenceFacts(
        candidate_tx_ids=[t.transaction_id for t in candidates],
        suspected_duplicate_id=dup_id,
        ambiguous=len(candidates) >= 2,
        no_history=len(hist) == 0,
        hints={name: _has(c, kws) for name, kws in _KW.items()},
        amounts=sorted(amts),
        counterparty_repeat=repeat,
        injection=_has(c, _INJECTION),
    )


# ── rules-only fallback (provisional; used when the LLM is unavailable) ────────
_SAFE_REPLY = (
    "Thank you for reaching out. We have logged your concern and our team will "
    "review it through official support channels. Please keep your account "
    "credentials private."
)
_SAFE_ACTION = "Route to the responsible team for review through official channels."


def _resp(req, *, case, dept, sev, verdict, rel, review, reply, codes) -> AnalyzeResponse:
    return AnalyzeResponse(
        ticket_id=req.ticket_id,
        relevant_transaction_id=rel,
        evidence_verdict=verdict,
        case_type=case,
        severity=sev,
        department=dept,
        agent_summary=f"Auto-triaged as {case} from the complaint and transaction history.",
        recommended_next_action=_SAFE_ACTION,
        customer_reply=reply,
        human_review_required=review,
        confidence=None,
        reason_codes=codes,
    )


def rules_verdict(req: AnalyzeRequest, facts: EvidenceFacts) -> AnalyzeResponse:
    """Deterministic routing when the LLM is off/slow/unavailable.

    Safe, schema-valid, escalates when unsure. Priority hierarchy:
    phishing > duplicate > cash_in > settlement > payment_failed >
    wrong_transfer > refund > other.
    """
    h = facts.hints
    hist = req.transaction_history

    if h["phishing"]:
        return _resp(
            req, case="phishing_or_social_engineering", dept="fraud_risk",
            sev="critical", verdict="insufficient_data", rel=None, review=True,
            reply=(
                "Thank you for reporting this. We never request your PIN, OTP, or "
                "password — please keep them private. Our fraud team will review "
                "this through official channels."
            ),
            codes=["phishing", "rules_fallback"],
        )

    if facts.suspected_duplicate_id:
        return _resp(
            req, case="duplicate_payment", dept="payments_ops", sev="high",
            verdict="consistent", rel=facts.suspected_duplicate_id, review=True,
            reply=_SAFE_REPLY, codes=["duplicate_payment", "rules_fallback"],
        )

    cash = _first(hist, type="cash_in")
    if h["cash_in"] and cash is not None:
        return _resp(
            req, case="agent_cash_in_issue", dept="agent_operations", sev="high",
            verdict="consistent", rel=cash.transaction_id, review=True,
            reply=_SAFE_REPLY, codes=["agent_cash_in_issue", "rules_fallback"],
        )

    settle = _first(hist, type="settlement")
    if h["settlement"] and settle is not None:
        return _resp(
            req, case="merchant_settlement_delay", dept="merchant_operations",
            sev="medium", verdict="consistent", rel=settle.transaction_id,
            review=False, reply=_SAFE_REPLY,
            codes=["merchant_settlement_delay", "rules_fallback"],
        )

    failed = _first(hist, status="failed")
    if h["payment_failed"] and failed is not None:
        # deducted-but-failed: user reports exactly the hold issue -> consistent.
        return _resp(
            req, case="payment_failed", dept="payments_ops", sev="high",
            verdict="consistent", rel=failed.transaction_id, review=False,
            reply=_SAFE_REPLY, codes=["payment_failed", "rules_fallback"],
        )

    if h["wrong_transfer"]:
        if facts.ambiguous:  # multiple equal matches -> don't guess
            return _resp(
                req, case="wrong_transfer", dept="dispute_resolution", sev="medium",
                verdict="insufficient_data", rel=None, review=False, reply=_SAFE_REPLY,
                codes=["wrong_transfer", "ambiguous_match", "rules_fallback"],
            )
        if len(facts.candidate_tx_ids) == 1:
            # habitual payee (>=3 transfers) contradicts an "accident" claim ->
            # inconsistent + flag the user; otherwise the match stands.
            repeat = facts.counterparty_repeat
            return _resp(
                # contradicted claim (habitual payee) is medium; a genuine matched
                # mis-send is high — mirrors the LLM-guard policy.
                req, case="wrong_transfer", dept="dispute_resolution",
                sev="medium" if repeat else "high",
                verdict="inconsistent" if repeat else "consistent",
                rel=facts.candidate_tx_ids[0], review=True, reply=_SAFE_REPLY,
                codes=["wrong_transfer", "transaction_match", "rules_fallback"]
                + (["counterparty_repeat", "flag_user"] if repeat else []),
            )
        return _resp(
            req, case="wrong_transfer", dept="dispute_resolution", sev="medium",
            verdict="insufficient_data", rel=None, review=True, reply=_SAFE_REPLY,
            codes=["wrong_transfer", "rules_fallback"],
        )

    if h["refund"]:
        rel = hist[0].transaction_id if hist else None
        return _resp(
            req, case="refund_request", dept="customer_support", sev="low",
            verdict="consistent" if hist else "insufficient_data", rel=rel,
            review=False, reply=_SAFE_REPLY, codes=["refund_request", "rules_fallback"],
        )

    return _resp(
        req, case="other", dept="customer_support", sev="low",
        verdict="insufficient_data", rel=None, review=False, reply=_SAFE_REPLY,
        codes=["insufficient_evidence", "rules_fallback"],
    )