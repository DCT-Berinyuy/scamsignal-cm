"""Reproduce every evaluation number in the README (PRD §10).

    python eval/eval.py               # rules-only and rules+model (needs GEMINI_API_KEY)
    python eval/eval.py --rules-only  # rules-only run only

Reads the human-written test set eval/testset/{en,fr,pcm}.jsonl and writes eval/results.md.
Nobody tunes rules or prompts on the test set; tune on eval/devset.jsonl instead.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from app.advice import default_advice  # noqa: E402
from app.config import (  # noqa: E402
    GEMINI_API_KEY_ENV,
    LANGS,
    MAX_TEXT_LEN,
    MODEL_ID,
    SENDER_TYPES,
    gemini_api_key,
)
from app.main import CheckRequest, analyze  # noqa: E402
from app.model import Assessor, GemmaClient  # noqa: E402
from app.rules import default_rules  # noqa: E402

DEFAULT_TESTSET_DIR = ROOT / "eval" / "testset"
DEFAULT_RESULTS = ROOT / "eval" / "results.md"
LABELS = ("suspicious", "unclear", "no_warning_signs")
FIELDS = ("id", "lang", "text", "sender_type", "expected", "scam_type", "paraphrased", "author")
RUNS = ("rules_only", "rules_model")
RUN_NAMES = {"rules_only": "rules only", "rules_model": "rules + model"}
RETRY_DELAY_S = 3.0


class EvalDataError(Exception):
    """The test set is missing or malformed. The message never contains message text."""


@dataclass(frozen=True)
class Item:
    id: str
    lang: str
    text: str
    sender_type: str
    expected: str
    paraphrased: bool

    @property
    def legitimate(self) -> bool:
        return self.expected == "no_warning_signs"


@dataclass(frozen=True)
class Outcome:
    item: Item
    rules_only: str
    rules_model: str | None  # None when the model run was skipped
    model_used: bool


# --- Loading ---------------------------------------------------------------------------------


def _parse_line(raw: str, lang: str, where: str) -> Item:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EvalDataError(f"{where}: not valid JSON ({exc.msg})") from None
    if not isinstance(data, dict):
        raise EvalDataError(f"{where}: each line must be a JSON object")
    missing = [f for f in FIELDS if f not in data]
    if missing:
        raise EvalDataError(f"{where}: missing field(s) {', '.join(missing)}")
    checks = [
        (isinstance(data["id"], str) and data["id"].strip(), "id must be a non-empty string"),
        (data["lang"] == lang, f"lang must be '{lang}' in this file"),
        (isinstance(data["text"], str) and 1 <= len(data["text"].strip()) and len(data["text"]) <= MAX_TEXT_LEN,
         f"text must be 1-{MAX_TEXT_LEN} characters"),
        (data["sender_type"] in SENDER_TYPES, f"sender_type must be one of {SENDER_TYPES}"),
        (data["expected"] in LABELS, f"expected must be one of {LABELS}"),
        (isinstance(data["paraphrased"], bool), "paraphrased must be true or false"),
    ]
    for ok, message in checks:
        if not ok:
            raise EvalDataError(f"{where}: {message}")
    return Item(data["id"], lang, data["text"], data["sender_type"], data["expected"], data["paraphrased"])


def load_testset(directory: Path = DEFAULT_TESTSET_DIR) -> list[Item]:
    files = {lang: directory / f"{lang}.jsonl" for lang in LANGS}
    missing = [str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p) for p in files.values() if not p.is_file()]
    if missing:
        raise EvalDataError(
            "test set not found: " + ", ".join(missing) + "\n"
            "The test set is written by humans (members B and C, PRD §9 and §14), never by an AI agent.\n"
            "Add the files, one JSON object per line with fields: " + ", ".join(FIELDS) + "."
        )
    items: list[Item] = []
    for lang, path in files.items():
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if raw.strip():
                items.append(_parse_line(raw, lang, f"{path.name}:{number}"))
    if not items:
        raise EvalDataError("test set files are empty")
    duplicates = [i for i, c in Counter(item.id for item in items).items() if c > 1]
    if duplicates:
        raise EvalDataError(f"duplicate id(s): {', '.join(sorted(duplicates))}")
    return items


# --- Running ---------------------------------------------------------------------------------


async def run_items(items: Sequence[Item], model: Assessor | None, retry_delay_s: float = RETRY_DELAY_S) -> list[Outcome]:
    rules, advice = default_rules(), default_advice()
    outcomes = []
    for item in items:
        req = CheckRequest(text=item.text, lang=item.lang, sender_type=item.sender_type)
        rules_only = await analyze(req, rules, advice, None)
        with_model = None
        if model is not None:
            with_model = await analyze(req, rules, advice, model)
            if not with_model.model_used:  # one retry for rate limits or a network blip
                await asyncio.sleep(retry_delay_s)
                with_model = await analyze(req, rules, advice, model)
        outcomes.append(
            Outcome(
                item=item,
                rules_only=rules_only.label.value,
                rules_model=with_model.label.value if with_model else None,
                model_used=bool(with_model and with_model.model_used),
            )
        )
    return outcomes


# --- Metrics (pure) --------------------------------------------------------------------------


def frac(k: int, n: int) -> str:
    return f"{k} / {n} ({100 * k / n:.0f}%)" if n else f"{k} / 0 (n/a)"


def flagged(label: str | None) -> bool:
    return label in ("suspicious", "unclear")


def label_quality(outcomes: Sequence[Outcome], run: str) -> dict[str, Any]:
    pred = [(o.item, getattr(o, run)) for o in outcomes]
    tp = sum(1 for i, p in pred if p == "suspicious" and i.expected == "suspicious")
    predicted = sum(1 for _, p in pred if p == "suspicious")
    expected = sum(1 for i, _ in pred if i.expected == "suspicious")
    legit = [(i, p) for i, p in pred if i.legitimate]
    return {
        "precision": frac(tp, predicted),
        "recall": frac(tp, expected),
        "fp_legit": frac(sum(1 for _, p in legit if p == "suspicious"), len(legit)),
    }


def why_ai(outcomes: Sequence[Outcome]) -> dict[str, Any]:
    para = [o for o in outcomes if o.item.paraphrased]
    missed = [o for o in para if o.rules_only == "no_warning_signs"]
    legit_clean = [o for o in outcomes if o.item.legitimate]
    return {
        "para_flagged_rules": frac(sum(flagged(o.rules_only) for o in para), len(para)),
        "para_flagged_model": frac(sum(flagged(o.rules_model) for o in para), len(para)),
        "para_raised": frac(sum(1 for o in missed if o.rules_model == "unclear"), len(missed)),
        "legit_cost": frac(
            sum(1 for o in legit_clean if o.rules_only == "no_warning_signs" and o.rules_model == "unclear"),
            len(legit_clean),
        ),
        "n_para": len(para),
        "n_missed": len(missed),
        "n_legit": len(legit_clean),
    }


def confusion(outcomes: Sequence[Outcome], run: str, lang: str | None = None) -> dict[str, Counter]:
    matrix = {label: Counter() for label in LABELS}
    for o in outcomes:
        if lang is None or o.item.lang == lang:
            matrix[o.item.expected][getattr(o, run)] += 1
    return matrix


def invariant_violations(outcomes: Sequence[Outcome]) -> list[str]:
    """Under PRD §7.2 the model never changes a 'suspicious' decision either way."""
    return [
        o.item.id
        for o in outcomes
        if o.rules_model is not None and (o.rules_only == "suspicious") != (o.rules_model == "suspicious")
    ]


# --- Report ----------------------------------------------------------------------------------


def _matrix_md(matrix: dict[str, Counter]) -> list[str]:
    lines = ["| expected \\ predicted | " + " | ".join(LABELS) + " | n |", "|---|" + "---|" * (len(LABELS) + 1)]
    for exp in LABELS:
        row = matrix[exp]
        lines.append(f"| {exp} | " + " | ".join(str(row[p]) for p in LABELS) + f" | {sum(row.values())} |")
    return lines


def render(outcomes: Sequence[Outcome], model_run: bool) -> str:
    n = len(outcomes)
    per_lang = Counter(o.item.lang for o in outcomes)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    runs = RUNS if model_run else ("rules_only",)
    out = [
        "# Evaluation results",
        "",
        f"Generated by `python eval/eval.py{'' if model_run else ' --rules-only'}` on {now}.",
        f"Model: `{MODEL_ID}` via the Gemini API (hosted, not pinned)." if model_run else "Model: not run.",
        f"Test set: n = {n} ({', '.join(f'{lang} {per_lang[lang]}' for lang in LANGS)}). "
        "With this sample size, results are indicative only.",
        "Legitimate = expected `no_warning_signs`. Flagged = `suspicious` or `unclear`.",
    ]
    if model_run:
        unavailable = sum(1 for o in outcomes if not o.model_used)
        out.append(f"Model unavailable (after one retry, counted as rules-only): {frac(unavailable, n)}.")
    out += ["", "## Table A: label quality (positive class = suspicious)", ""]
    out += ["| Run | Precision | Recall | False positives among legitimate |", "|---|---|---|---|"]
    for run in runs:
        q = label_quality(outcomes, run)
        out.append(f"| {RUN_NAMES[run]} | {q['precision']} | {q['recall']} | {q['fp_legit']} |")
    if model_run:
        violations = invariant_violations(outcomes)
        out += ["", "Invariant check (model never changes a suspicious decision): "
                + ("OK" if not violations else f"VIOLATED for {', '.join(violations)}")]
        b = why_ai(outcomes)
        out += [
            "",
            "## Table B: why AI (what the model adds)",
            "",
            "| | Rules only | Rules + model | n |",
            "|---|---|---|---|",
            f"| Paraphrased scams flagged | {b['para_flagged_rules']} | {b['para_flagged_model']} | {b['n_para']} |",
            f"| Paraphrased scams the rules missed that the model raised to unclear | — | {b['para_raised']} | {b['n_missed']} |",
            f"| Cost: legitimate messages wrongly raised to unclear by the model | — | {b['legit_cost']} | {b['n_legit']} |",
        ]
    final = runs[-1]
    out += ["", f"## Confusion matrices ({RUN_NAMES[final]})", ""]
    for lang in LANGS:
        out += [f"### {lang} (n = {per_lang[lang]})", "", *_matrix_md(confusion(outcomes, final, lang)), ""]
    out += [f"### all (n = {n})", "", *_matrix_md(confusion(outcomes, final)), ""]
    out += ["## Misclassified ids", "", "Message text is not repeated here; look ids up in eval/testset/.", ""]
    for run in runs:
        wrong = [f"{o.item.id} (expected {o.item.expected}, got {getattr(o, run)})"
                 for o in outcomes if getattr(o, run) != o.item.expected]
        out.append(f"- {RUN_NAMES[run]} ({len(wrong)} / {n}): " + ("; ".join(wrong) if wrong else "none"))
    return "\n".join(out) + "\n"


# --- CLI -------------------------------------------------------------------------------------


async def _evaluate(items: Sequence[Item], rules_only: bool) -> list[Outcome]:
    if rules_only:
        return await run_items(items, None)
    async with httpx.AsyncClient() as http:
        return await run_items(items, GemmaClient(gemini_api_key() or "", http))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rules-only", action="store_true", help="skip the model run")
    parser.add_argument("--testset-dir", type=Path, default=DEFAULT_TESTSET_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--out", type=Path, default=DEFAULT_RESULTS, help="where to write the markdown report")
    args = parser.parse_args(argv)

    try:
        items = load_testset(args.testset_dir)
    except EvalDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not args.rules_only and not gemini_api_key():
        print(f"error: {GEMINI_API_KEY_ENV} is not set. Load .env first, or pass --rules-only.", file=sys.stderr)
        return 2

    print(f"Evaluating n = {len(items)} messages ({'rules only' if args.rules_only else 'rules only + rules+model'})...",
          file=sys.stderr)
    outcomes = asyncio.run(_evaluate(items, args.rules_only))
    report = render(outcomes, model_run=not args.rules_only)
    args.out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Written to {args.out}", file=sys.stderr)
    return 1 if invariant_violations(outcomes) else 0


if __name__ == "__main__":
    sys.exit(main())
