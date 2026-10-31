"""Human-written advice and 'why' templates (PRD §7.3). Never model-generated."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.config import ADVICE_PATH, LANGS
from app.rules import RuleHit, Severity

REQUIRED_LANGS = ("en", "fr")  # pcm may be missing: falls back to English (PRD §6 cut order)


class AdviceConfigError(ValueError):
    """advice.json is malformed. Raised at load time."""


@dataclass(frozen=True)
class AdviceBook:
    entries: Mapping[str, Mapping[str, str]]
    why_hits: Mapping[str, str]
    why_no_hits: Mapping[str, str]

    def advice(self, hits: Iterable[RuleHit], lang: str) -> str:
        """Pick by the highest-severity hit; hits keep rules.json order within a severity."""
        hits = tuple(hits)
        top = next((h for h in hits if h.severity == Severity.HARD), hits[0] if hits else None)
        key = top.id if top else "no_hits"
        entry = self.entries.get(key, self.entries["default"])
        return _pick(entry, lang)

    def why_template(self, reasons: list[str], has_hits: bool, lang: str) -> str:
        if not has_hits:
            return _pick(self.why_no_hits, lang)
        return _pick(self.why_hits, lang).format(reasons="; ".join(reasons))


def _pick(entry: Mapping[str, str], lang: str) -> str:
    return entry.get(lang) or entry["en"]


def _lang_entry(raw: Any, where: str, needs_placeholder: bool = False) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise AdviceConfigError(f"{where}: must be an object")
    for lang in REQUIRED_LANGS:
        if not isinstance(raw.get(lang), str) or not raw[lang].strip():
            raise AdviceConfigError(f"{where}: missing '{lang}' text")
    entry = {lang: raw[lang] for lang in LANGS if isinstance(raw.get(lang), str) and raw[lang].strip()}
    if needs_placeholder and any("{reasons}" not in text for text in entry.values()):
        raise AdviceConfigError(f"{where}: every language needs the {{reasons}} placeholder")
    return entry


def parse_advice(data: Any) -> AdviceBook:
    if not isinstance(data, dict) or not isinstance(data.get("advice"), dict):
        raise AdviceConfigError("advice file needs an 'advice' object")
    entries = {key: _lang_entry(raw, f"advice.{key}") for key, raw in data["advice"].items()}
    for key in ("no_hits", "default"):
        if key not in entries:
            raise AdviceConfigError(f"advice.{key} is required")
    why = data.get("why_template")
    if not isinstance(why, dict):
        raise AdviceConfigError("why_template is required")
    return AdviceBook(
        entries=entries,
        why_hits=_lang_entry(why.get("hits"), "why_template.hits", needs_placeholder=True),
        why_no_hits=_lang_entry(why.get("no_hits"), "why_template.no_hits"),
    )


def load_advice(path: Path = ADVICE_PATH) -> AdviceBook:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdviceConfigError(f"cannot read {path.name}: {exc}") from exc
    return parse_advice(data)


@lru_cache(maxsize=1)
def default_advice() -> AdviceBook:
    return load_advice()
