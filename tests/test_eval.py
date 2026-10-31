"""eval/eval.py tests. Fixtures are tiny developer-written messages in tmp dirs, never the real test set."""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from app.combine import ModelVote
from app.model import ModelResult

_SPEC = importlib.util.spec_from_file_location(
    "eval_script", Path(__file__).resolve().parent.parent / "eval" / "eval.py"
)
ev = importlib.util.module_from_spec(_SPEC)
sys.modules["eval_script"] = ev  # dataclasses look the module up while it executes
_SPEC.loader.exec_module(ev)

SCAM = "Congratulations, you won! Send your PIN to 6XX XXX XXX."
LEGIT = "Transfer of 5000 FCFA to JOHN D successful. Never share your PIN."
PARA = "Hi, it's your uncle on a new line. Kindly help me with something small."


def line(id_, lang, text, expected, paraphrased=False, sender="number") -> str:
    return json.dumps({
        "id": id_, "lang": lang, "text": text, "sender_type": sender, "expected": expected,
        "scam_type": None if expected == "no_warning_signs" else "x", "paraphrased": paraphrased, "author": "unit-test",
    })


def write_set(directory: Path, rows: dict[str, list[str]]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for lang, lines in rows.items():
        (directory / f"{lang}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return directory


@pytest.fixture()
def small_set(tmp_path) -> Path:
    return write_set(tmp_path / "testset", {
        "en": [line("en-1", "en", SCAM, "suspicious"), line("en-2", "en", LEGIT, "no_warning_signs", sender="named"),
               line("en-3", "en", PARA, "unclear", paraphrased=True, sender="unknown")],
        "fr": [line("fr-1", "fr", "Envoyez votre code secret maintenant.", "suspicious")],
        "pcm": [line("pcm-1", "pcm", "Send your PIN quick quick.", "suspicious")],
    })


class FakeModel:
    def __init__(self, vote: ModelVote | None) -> None:
        self.vote = vote

    async def assess(self, text, lang, sender_type, rule_reasons):
        return ModelResult(self.vote, None) if self.vote else None


# --- Loading ---------------------------------------------------------------------------------


def test_missing_testset_gives_clear_message(tmp_path, capsys) -> None:
    code = ev.main(["--rules-only", "--testset-dir", str(tmp_path / "nope"), "--out", str(tmp_path / "r.md")])
    err = capsys.readouterr().err
    assert code == 2
    assert "test set not found" in err and "en.jsonl" in err and "never by an AI agent" in err
    assert not (tmp_path / "r.md").exists()


def test_one_missing_language_file_is_reported(tmp_path) -> None:
    d = write_set(tmp_path / "ts", {"en": [line("e", "en", SCAM, "suspicious")]})
    with pytest.raises(ev.EvalDataError, match="fr.jsonl.*pcm.jsonl"):
        ev.load_testset(d)


@pytest.mark.parametrize(
    "bad,match",
    [
        ("{not json", "en.jsonl:1: not valid JSON"),
        (json.dumps({"id": "x"}), "missing field"),
        (line("x", "fr", SCAM, "suspicious"), "lang must be 'en'"),
        (line("x", "en", SCAM, "safe"), "expected must be one of"),
        (line("x", "en", "a" * 1001, "suspicious"), "text must be"),
    ],
)
def test_malformed_lines_are_reported_without_text(tmp_path, bad, match) -> None:
    d = write_set(tmp_path / "ts", {"en": [bad], "fr": [], "pcm": []})
    with pytest.raises(ev.EvalDataError, match=match) as exc:
        ev.load_testset(d)
    assert SCAM not in str(exc.value)


def test_duplicate_ids_rejected(tmp_path) -> None:
    d = write_set(tmp_path / "ts", {"en": [line("dup", "en", SCAM, "suspicious")],
                                    "fr": [line("dup", "fr", SCAM, "suspicious")], "pcm": []})
    with pytest.raises(ev.EvalDataError, match="duplicate id"):
        ev.load_testset(d)


def test_model_run_without_key_fails_clearly(small_set, tmp_path, capsys) -> None:
    code = ev.main(["--testset-dir", str(small_set), "--out", str(tmp_path / "r.md")])
    assert code == 2
    assert "GEMINI_API_KEY is not set" in capsys.readouterr().err


# --- Running and metrics ---------------------------------------------------------------------


def test_rules_only_report(small_set, tmp_path) -> None:
    out = tmp_path / "results.md"
    assert ev.main(["--rules-only", "--testset-dir", str(small_set), "--out", str(out)]) == 0
    report = out.read_text()
    assert "n = 5 (en 3, fr 1, pcm 1)" in report
    assert "| rules only | 3 / 3 (100%) | 3 / 3 (100%) | 0 / 1 (0%) |" in report
    assert "Table B" not in report
    assert "en-3 (expected unclear, got no_warning_signs)" in report
    assert PARA not in report and SCAM not in report  # ids only, never text


def test_model_run_tables(small_set) -> None:
    items = ev.load_testset(small_set)
    outcomes = asyncio.run(ev.run_items(items, FakeModel(ModelVote.UNCLEAR), retry_delay_s=0))
    b = ev.why_ai(outcomes)
    assert b["para_flagged_rules"] == "0 / 1 (0%)"
    assert b["para_flagged_model"] == "1 / 1 (100%)"
    assert b["para_raised"] == "1 / 1 (100%)"
    assert b["legit_cost"] == "1 / 1 (100%)"  # the fake model also raised the legit message
    assert ev.invariant_violations(outcomes) == []
    report = ev.render(outcomes, model_run=True)
    assert "Model unavailable (after one retry, counted as rules-only): 0 / 5 (0%)" in report
    assert "Invariant check (model never changes a suspicious decision): OK" in report
    assert "### all (n = 5)" in report


def test_unavailable_model_is_counted(small_set) -> None:
    items = ev.load_testset(small_set)
    outcomes = asyncio.run(ev.run_items(items, FakeModel(None), retry_delay_s=0))
    assert all(not o.model_used for o in outcomes)
    assert "Model unavailable (after one retry, counted as rules-only): 5 / 5 (100%)" in ev.render(outcomes, True)


def test_confusion_matrix_counts() -> None:
    item = ev.Item("a", "en", "t", "number", "suspicious", False)
    outcomes = [ev.Outcome(item, "unclear", "unclear", True), ev.Outcome(item, "suspicious", "suspicious", True)]
    m = ev.confusion(outcomes, "rules_model", "en")
    assert m["suspicious"]["unclear"] == 1 and m["suspicious"]["suspicious"] == 1
    assert sum(m["no_warning_signs"].values()) == 0


def test_frac_handles_zero() -> None:
    assert ev.frac(0, 0) == "0 / 0 (n/a)"
    assert ev.frac(1, 3) == "1 / 3 (33%)"
