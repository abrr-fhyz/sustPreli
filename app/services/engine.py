"""The investigator — hybrid engine orchestrator.

Flow: deterministic evidence pre-pass grounds the facts -> Gemini judges
(classification, verdict nuance, multilingual reply) -> on no-key/timeout/error
we fall back to the rules-only verdict. The outgoing safety net (scrub_response)
runs in the route, over whatever this returns. Never raises.
"""
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.evidence import ground_evidence, rules_verdict
from app.services.llm import triage


def investigate(req: AnalyzeRequest) -> AnalyzeResponse:
    facts = ground_evidence(req)

    llm_out = triage(req, facts)  # None when LLM unavailable
    if llm_out is not None:
        return llm_out

    # Fallback (provisional, pending the strategy decision): deterministic rules.
    return rules_verdict(req, facts)
