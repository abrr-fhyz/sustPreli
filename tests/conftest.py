"""Default test runs are offline + deterministic.

A real GEMINI_API_KEY in .env would otherwise make every endpoint test hit the
live Gemini API (slow, flaky, costs money). This autouse fixture stubs the LLM
call so the engine takes its deterministic rules path. Set RUN_LLM_TESTS=1 to
exercise the live API (see tests/test_sample_cases.py Tier B).
"""
import os

import pytest


@pytest.fixture(autouse=True)
def _force_rules_unless_llm(monkeypatch):
    if not os.getenv("RUN_LLM_TESTS"):
        monkeypatch.setattr("app.services.engine.triage", lambda req, facts: None)
