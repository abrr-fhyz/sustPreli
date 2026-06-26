import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PORT: int = int(os.getenv("PORT", 8000))
    API_KEY: str = os.getenv("API_KEY", "")

settings = Settings()
