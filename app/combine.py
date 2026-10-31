"""Decision table (PRD §7.2). Rules decide first; the model can only raise a clean message to unclear."""

from __future__ import annotations

from enum import Enum
from typing import Iterable

from app.rules import RuleHit, Severity


class Label(str, Enum):
    SUSPICIOUS = "suspicious"
    UNCLEAR = "unclear"
    NO_WARNING_SIGNS = "no_warning_signs"


class ModelVote(str, Enum):
    SUSPICIOUS = "suspicious"
    UNCLEAR = "unclear"
    SAFE = "safe"


def combine(hits: Iterable[RuleHit], vote: ModelVote | None) -> Label:
    """vote=None means the model was unavailable (timeout, error, no key)."""
    hits = tuple(hits)
    if any(h.severity == Severity.HARD for h in hits):
        return Label.SUSPICIOUS  # row 1
    soft_count = len({h.id for h in hits if h.severity == Severity.SOFT})
    if soft_count >= 2:
        return Label.SUSPICIOUS  # row 2
    if soft_count == 1:
        return Label.UNCLEAR  # row 3
    if vote in (ModelVote.SUSPICIOUS, ModelVote.UNCLEAR):
        return Label.UNCLEAR  # row 4: the model alone never yields suspicious
    return Label.NO_WARNING_SIGNS  # row 5
