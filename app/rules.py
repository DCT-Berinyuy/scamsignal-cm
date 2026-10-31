"""Rule engine (PRD §7.1, §8.3): normalize, mask warning phrases, then match rules from rules/rules.json."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from app.config import LANGS, RULES_PATH, SENDER_TYPES

MAX_REASONS = 4
_HOST_RE = re.compile(r"^(?:https?://)?(?:www\.)?([^/\s:?#]+)")


class Severity(str, Enum):
    HARD = "hard"
    SOFT = "soft"


class RulesConfigError(ValueError):
    """rules.json is malformed. Raised at load time so a bad rules file fails fast."""


@dataclass(frozen=True)
class RuleHit:
    id: str
    severity: Severity


@dataclass(frozen=True)
class Rule:
    id: str
    severity: Severity
    patterns: tuple[re.Pattern[str], ...]
    reason: Mapping[str, str]
    sender_types: frozenset[str] | None = None
    allow: tuple[str, ...] = ()

    def matches(self, text: str, sender_type: str) -> bool:
        if self.sender_types is not None and sender_type not in self.sender_types:
            return False
        return any(
            not self._allowed(m.group(0)) for p in self.patterns for m in p.finditer(text)
        )

    def _allowed(self, matched: str) -> bool:
        if not self.allow:
            return False
        host_match = _HOST_RE.match(matched)
        host = host_match.group(1).rstrip(".") if host_match else ""
        return any(host == d or host.endswith("." + d) for d in self.allow)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Lowercase, strip accents, unify apostrophes and collapse spaces (newlines kept)."""
    unified = strip_accents(text).replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
    return re.sub(r"[ \t]+", " ", unified.lower())


@dataclass(frozen=True)
class RuleSet:
    mask: tuple[re.Pattern[str], ...]
    rules: tuple[Rule, ...]
    no_hits_reason: Mapping[str, str]

    def masked(self, text: str) -> str:
        """Blank out each warning phrase. Per phrase, not per message (PRD §7.1)."""
        result = normalize(text)
        for phrase in self.mask:
            result = phrase.sub(" ", result)
        return result

    def check(self, text: str, sender_type: str) -> tuple[RuleHit, ...]:
        prepared = self.masked(text)
        return tuple(
            RuleHit(rule.id, rule.severity) for rule in self.rules if rule.matches(prepared, sender_type)
        )

    def reasons(self, hits: tuple[RuleHit, ...], lang: str) -> list[str]:
        """1-4 reasons in the chosen language, hard hits first (PRD §7.3)."""
        if not hits:
            return [self.no_hits_reason[lang]]
        by_id = {rule.id: rule for rule in self.rules}
        ordered = sorted(hits, key=lambda h: h.severity != Severity.HARD)
        return [by_id[h.id].reason[lang] for h in ordered][:MAX_REASONS]


def _compile(pattern: str, where: str) -> re.Pattern[str]:
    try:
        # Accents only: lowercasing a regex would turn \S into \s, \W into \w.
        return re.compile(strip_accents(pattern), re.IGNORECASE)
    except re.error as exc:
        raise RulesConfigError(f"{where}: invalid regex ({exc})") from exc


def _mask_pattern(phrase: str) -> re.Pattern[str]:
    words = [re.escape(w) for w in normalize(phrase).split()]
    if not words:
        raise RulesConfigError("mask: empty phrase")
    return re.compile(r"(?<!\w)" + r"\s+".join(words) + r"(?!\w)")


def _lang_map(raw: Any, where: str) -> dict[str, str]:
    if not isinstance(raw, dict) or any(not isinstance(raw.get(lang), str) or not raw[lang] for lang in LANGS):
        raise RulesConfigError(f"{where}: needs non-empty text for {', '.join(LANGS)}")
    return {lang: raw[lang] for lang in LANGS}


def _parse_rule(raw: Any, index: int) -> Rule:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
        raise RulesConfigError(f"rules[{index}]: missing id")
    rid = raw["id"]
    try:
        severity = Severity(raw.get("severity"))
    except ValueError as exc:
        raise RulesConfigError(f"{rid}: severity must be 'hard' or 'soft'") from exc
    patterns = raw.get("patterns")
    if not isinstance(patterns, list) or not patterns or not all(isinstance(p, str) for p in patterns):
        raise RulesConfigError(f"{rid}: patterns must be a non-empty list of strings")
    sender_types = raw.get("sender_types")
    if sender_types is not None and (
        not isinstance(sender_types, list) or not set(sender_types) <= set(SENDER_TYPES)
    ):
        raise RulesConfigError(f"{rid}: sender_types must be a subset of {SENDER_TYPES}")
    allow = raw.get("allow", [])
    if not isinstance(allow, list) or not all(isinstance(d, str) for d in allow):
        raise RulesConfigError(f"{rid}: allow must be a list of domains")
    return Rule(
        id=rid,
        severity=severity,
        patterns=tuple(_compile(p, f"{rid}.patterns[{i}]") for i, p in enumerate(patterns)),
        reason=_lang_map(raw.get("reason"), f"{rid}.reason"),
        sender_types=frozenset(sender_types) if sender_types is not None else None,
        allow=tuple(normalize(d).strip() for d in allow),
    )


def parse_rules(data: Any) -> RuleSet:
    if not isinstance(data, dict):
        raise RulesConfigError("rules file must be a JSON object")
    mask = data.get("mask", [])
    if not isinstance(mask, list) or not all(isinstance(m, str) for m in mask):
        raise RulesConfigError("mask must be a list of strings")
    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise RulesConfigError("rules must be a non-empty list")
    rules = tuple(_parse_rule(r, i) for i, r in enumerate(raw_rules))
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise RulesConfigError("rule ids must be unique")
    # Longest phrases first so "no give anybody" is masked before "no give".
    phrases = sorted({normalize(m).strip() for m in mask if m.strip()}, key=len, reverse=True)
    return RuleSet(
        mask=tuple(_mask_pattern(p) for p in phrases),
        rules=rules,
        no_hits_reason=_lang_map(data.get("no_hits_reason"), "no_hits_reason"),
    )


def load_rules(path: Path = RULES_PATH) -> RuleSet:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RulesConfigError(f"cannot read {path.name}: {exc}") from exc
    return parse_rules(data)


@lru_cache(maxsize=1)
def default_rules() -> RuleSet:
    return load_rules()
