"""The investigator — hybrid engine orchestrator.

Flow: deterministic evidence pre-pass grounds the facts -> Gemini judges
(classification, verdict nuance, multilingual reply) -> on no-key/timeout/error
we fall back to the rules-only verdict. The outgoing safety net (scrub_response)
runs in the route, over whatever this returns. Never raises.
"""
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.evidence import _SAFE_REPLY, ground_evidence, rules_verdict
from app.services.llm import triage


def investigate(req: AnalyzeRequest) -> AnalyzeResponse:
    facts = ground_evidence(req)

    llm_out = triage(req, facts)  # None when LLM unavailable
    resp = llm_out if llm_out is not None else rules_verdict(req, facts)

    # Prompt-injection / impersonation guard (both tiers): authority-spoofing text
    # is never legitimate -> force human review and swap the reply for a safe canned
    # one so no injected token (auth code, fake amount) is echoed back at the user.
    if facts.injection:
        codes = list(resp.reason_codes or [])
        if "prompt_injection_signal" not in codes:
            codes.append("prompt_injection_signal")
        resp = resp.model_copy(update={
            "human_review_required": True,
            "customer_reply": _SAFE_REPLY,
            "reason_codes": codes,
        })
    return resp