"""Configuration, read from the environment (and a .env file if present)."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
API_KEY = os.getenv("ANTHROPIC_API_KEY") or None
# Use a current, valid alias. claude-haiku-4-5 is the cheapest and is plenty for
# this task. Other valid ids: claude-sonnet-5, claude-opus-4-8.
MODEL = os.getenv("MODEL", "claude-haiku-4-5")
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "editorial_guard.db"))
