from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
class Settings:
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "")
    LLM_CONNECT_TIMEOUT = float(os.getenv("LLM_CONNECT_TIMEOUT", "10"))
    LLM_READ_TIMEOUT = float(os.getenv("LLM_READ_TIMEOUT", "300"))
    AGENT_MAX_ROUNDS = int(os.getenv("AGENT_MAX_ROUNDS", "8"))
