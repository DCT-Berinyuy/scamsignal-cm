"""Single source of configuration. APP_NAME lives here and nowhere else in code."""

import os
from pathlib import Path

APP_NAME = "ScamSignal CM"

ROOT_DIR = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT_DIR / "rules" / "rules.json"
ADVICE_PATH = ROOT_DIR / "advice" / "advice.json"
STATIC_DIR = ROOT_DIR / "static"

# Input limits and allowed values (PRD §6, §8.2)
MAX_TEXT_LEN = 1000
LANGS = ("en", "fr", "pcm")
DEFAULT_LANG = "en"
SENDER_TYPES = ("named", "number", "unknown")

# Model (PRD v3.2 §0): Gemma 4 hosted on the Gemini API. Hosted models cannot be pinned to a commit.
MODEL_ID = "gemma-4-26b-a4b-it"
MODEL_LICENSE = "Apache-2.0 (Gemma 4 weights); hosted use is under the Gemini API terms"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
MODEL_TIMEOUT_S = 8.0
WHY_MAX_OUTPUT_TOKENS = 100


def gemini_api_key() -> str | None:
    """Read the API key from the environment. Never hard-code or log it."""
    key = os.environ.get(GEMINI_API_KEY_ENV, "").strip()
    return key or None
