"""Outgoing-reply safety net.

Runs on the response we are about to return — the last line of defence even
if a heuristic or LLM produces an unsafe reply. Detect + scrub, never trust.
Rules mirror the rubric penalties.
"""
import re

from app.models.schemas import AnalyzeResponse

# Safe canned replacements (obey "official channels", no promises, no credentials).
SAFE_REPLY = (
    "Thank you for reaching out. We have logged your concern and our team is "
    "reviewing it. Any eligible amount will be returned through official channels. "
    "Please keep your account credentials private and never share them with anyone."
)
SAFE_ACTION = "Escalate to the responsible team for verification through official channels."

# ── detectors ─────────────────────────────────────────────────────────────────
# The rule is never to ASK for a credential, so a credential token only counts
# as a violation when a request verb sits next to it. This lets safe warnings
# ("never share your PIN") pass while catching "send your OTP".
# ponytail: verb-before-token proximity; bare "your OTP is needed" slips past —
# acceptable for a net, the engine is the primary guard.
_CRED_TOKEN = (
    r"(pin|otp|one[\s-]?time[\s-]?password|password|cvv|cvc|"
    r"card\s*(number|no\.?|#)|full\s*card)"
)
_CREDENTIAL = re.compile(
    r"\b(share|send|provide|give|enter|tell|confirm|verify|need|type|input|"
    r"submit|reply\s+with|forward|resend|ask\s+for)\b[^.?!]{0,40}?\b" + _CRED_TOKEN + r"\b",
    re.IGNORECASE,
)
# Negated/warning context ("we never ask for your OTP", "do not share your PIN")
# is SAFE, not a request. Detected so the net does not clobber correct warnings.
_CRED_NEGATED = re.compile(
    r"\b(never|not|n't|do\s+not|don'?t|avoid|without|keep[^.?!]{0,20}private)\b"
    r"[^.?!]{0,40}?\b(share|send|provide|give|enter|tell|confirm|verify|ask|"
    r"disclose|reveal|request)\b[^.?!]{0,40}?\b" + _CRED_TOKEN + r"\b",
    re.IGNORECASE,
)


def _asks_credential(text: str) -> bool:
    return bool(_CREDENTIAL.search(text)) and not _CRED_NEGATED.search(text)
# "we will refund / have reversed / will unblock / account unblocked ..."
_PROMISE = re.compile(
    r"\b(we\s+(will|have|are\s+going\s+to)\s+"
    r"(refund|reverse|return|unblock|recover|restore|credit)|"
    r"(refund(ed)?|reversed|unblocked|recovered|restored)\s+(you|your|the\s+(account|amount|money|customer))|"
    r"(will|has|have|had)\s+(been|be)\s+(refunded|reversed|unblocked|recovered|restored|credited))\b",
    re.IGNORECASE,
)
# off-channel / untrusted contact points
_THIRD_PARTY = re.compile(
    r"\b(whatsapp|telegram|viber|imo|messenger)\b|https?://|bit\.ly|t\.me|"
    r"\bclick\s+(this|here|the)\s+link\b",
    re.IGNORECASE,
)


def reply_violations(text: str) -> list[str]:
    """Return labels for any safety rule the text breaks (empty = safe)."""
    out = []
    if _asks_credential(text):
        out.append("credential_request")
    if _PROMISE.search(text):
        out.append("unauthorized_promise")
    if _THIRD_PARTY.search(text):
        out.append("third_party_referral")
    return out


def scrub_response(resp: AnalyzeResponse) -> AnalyzeResponse:
    """Return a copy with any unsafe customer_reply / next_action neutralised.

    On any violation we swap the whole field for a safe canned string — a net,
    not a rewrite. Safe responses pass through unchanged (==).
    """
    reply = resp.customer_reply
    action = resp.recommended_next_action
    changed = False

    if reply_violations(reply):
        reply = SAFE_REPLY
        changed = True
    # next_action only judged on promises/credentials (it's internal-facing, but
    # the rubric still penalises unauthorized promises here).
    if _PROMISE.search(action) or _asks_credential(action):
        action = SAFE_ACTION
        changed = True

    if not changed:
        return resp
    return resp.model_copy(update={"customer_reply": reply, "recommended_next_action": action})
