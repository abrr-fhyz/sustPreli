BLOCKED_KEYWORDS = ["password", "credit card", "ssn", "social security", "api_key"]

def safety_filter(text: str) -> bool:
    """
    Returns True if input is safe, False if it contains blocked keywords.
    """
    lowered = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in lowered:
            return False
    return True
