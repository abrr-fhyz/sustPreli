BLOCKED_KEYWORDS = [
    "password",
    "credit card",
    "ssn",
    "social security",
    "api_key",

    # prompt injection attempts
    "ignore previous instructions",
    "ignore all instructions",
    "disregard system prompt",
    "system prompt",
    "developer instructions"
]


def safety_filter(text: str) -> bool:
    """
    Basic prompt-injection and malicious input detection.
    Returns True if safe.
    """

    if not text or not text.strip():
        return False

    lowered = text.lower()

    for keyword in BLOCKED_KEYWORDS:
        if keyword in lowered:
            return False

    return True