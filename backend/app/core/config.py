# backend/app/core/config.py
import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=ROOT_ENV, override=True)

class Settings(BaseModel):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    NEO4J_URI: str = os.getenv("NEO4J_URI", "")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")

settings = Settings()
