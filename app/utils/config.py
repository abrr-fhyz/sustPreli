import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    PORT: int = int(os.getenv("PORT", 8000))
    API_KEY: str = os.getenv("API_KEY", "")

    # Gemini LLM (the "judge" half of the hybrid engine). Absent key -> rules-only.
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    LLM_TIMEOUT_S: float = float(os.getenv("LLM_TIMEOUT_S", "8"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))


settings = Settings()
