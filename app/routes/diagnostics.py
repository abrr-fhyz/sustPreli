"""Operational diagnostics — not part of the scored contract.

GET /llm-check verifies the Gemini key is present and can actually generate,
so you can confirm the engine is live before submission. Never leaks the key.
"""
from fastapi import APIRouter

from app.services.llm import key_check

router = APIRouter()


@router.get("/llm-check")
def llm_check():
    return key_check()
