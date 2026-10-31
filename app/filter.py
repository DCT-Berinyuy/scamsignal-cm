"""Output filter for the model's "why" (PRD §8.4). Rejected text falls back to the template."""

from __future__ import annotations

import re

from app.rules import RuleSet, default_rules

MAX_WHY_SENTENCES = 2
MAX_WHY_CHARS = 320

_DIGIT = re.compile(r"\d")
_URL = re.compile(
    r"https?://|\bwww\.|\b[a-z0-9-]+\.(com|net|org|cm|ly|me|xyz|info|top|io|co|link|site|online|click|biz|app|gl|to|cc)\b",
    re.IGNORECASE,
)
_PHONE = re.compile(r"\b6[0-9x]{2}[\s.-]?[0-9x]{3}[\s.-]?[0-9x]{3}\b|\+\s*237", re.IGNORECASE)
# Matched on the lowercased text with accents kept: "sûr" (safe) must not catch the preposition "sur" (on).
_SAFETY = re.compile(
    r"\b(safe\w*|legit\w*|genuine\w*|authenti\w*|sûre?s?|sans danger|sans risque)\b"
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def is_rejected(why: str, rules: RuleSet | None = None) -> bool:
    lowered = why.lower()
    if _DIGIT.search(why) or _URL.search(why) or _PHONE.search(why) or _SAFETY.search(lowered):
        return True
    # Any text telling the user to share a PIN/OTP: reuse the rule engine (warnings are masked out).
    hits = (rules or default_rules()).check(why, "unknown")
    return any(h.id == "pin_request" for h in hits)


def clean_why(raw: str | None, rules: RuleSet | None = None) -> str | None:
    """Return a ≤2-sentence why, or None if it must be replaced by the template."""
    if not raw:
        return None
    collapsed = " ".join(raw.split())
    sentences = [s for s in _SENTENCE_END.split(collapsed) if s]
    why = " ".join(sentences[:MAX_WHY_SENTENCES]).strip()
    if not why or len(why) > MAX_WHY_CHARS or is_rejected(why, rules):
        return None
    return why
