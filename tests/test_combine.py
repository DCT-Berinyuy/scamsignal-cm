"""Decision table (PRD §7.2): every row and every invariant."""

import itertools

import pytest

from app.combine import Label, ModelVote, combine
from app.rules import RuleHit, Severity

HARD = RuleHit("pin_request", Severity.HARD)
SOFT_A = RuleHit("urgency_threat", Severity.SOFT)
SOFT_B = RuleHit("link", Severity.SOFT)
ALL_VOTES = [None, *ModelVote]
SEVERITY_ORDER = {Label.NO_WARNING_SIGNS: 0, Label.UNCLEAR: 1, Label.SUSPICIOUS: 2}

HIT_SETS = {
    "none": (),
    "hard": (HARD,),
    "hard+soft": (HARD, SOFT_A),
    "one soft": (SOFT_A,),
    "two soft": (SOFT_A, SOFT_B),
}


@pytest.mark.parametrize("vote", ALL_VOTES)
def test_row1_any_hard_hit_is_suspicious(vote) -> None:
    assert combine((HARD,), vote) == Label.SUSPICIOUS
    assert combine((HARD, SOFT_A), vote) == Label.SUSPICIOUS


@pytest.mark.parametrize("vote", ALL_VOTES)
def test_row2_two_soft_hits_are_suspicious(vote) -> None:
    assert combine((SOFT_A, SOFT_B), vote) == Label.SUSPICIOUS


@pytest.mark.parametrize("vote", ALL_VOTES)
def test_row3_one_soft_hit_is_unclear(vote) -> None:
    assert combine((SOFT_A,), vote) == Label.UNCLEAR


def test_same_soft_rule_twice_counts_once() -> None:
    assert combine((SOFT_A, SOFT_A), None) == Label.UNCLEAR


@pytest.mark.parametrize("vote", [ModelVote.SUSPICIOUS, ModelVote.UNCLEAR])
def test_row4_clean_message_model_concern_is_unclear(vote) -> None:
    assert combine((), vote) == Label.UNCLEAR


@pytest.mark.parametrize("vote", [ModelVote.SAFE, None])
def test_row5_clean_and_model_safe_or_unavailable(vote) -> None:
    assert combine((), vote) == Label.NO_WARNING_SIGNS


# --- Invariants -------------------------------------------------------------------------------


@pytest.mark.parametrize("name,hits,vote", [(n, h, v) for (n, h), v in itertools.product(HIT_SETS.items(), ALL_VOTES)])
def test_invariant_model_never_lowers_rules_label(name, hits, vote) -> None:
    rules_only = combine(hits, None)
    assert SEVERITY_ORDER[combine(hits, vote)] >= SEVERITY_ORDER[rules_only]


@pytest.mark.parametrize("name", ["hard", "hard+soft", "one soft", "two soft"])
def test_invariant_rule_labels_ignore_model_vote(name) -> None:
    hits = HIT_SETS[name]
    assert {combine(hits, v) for v in ALL_VOTES} == {combine(hits, None)}


@pytest.mark.parametrize("vote", ALL_VOTES)
def test_invariant_model_alone_never_suspicious(vote) -> None:
    assert combine((), vote) != Label.SUSPICIOUS


def test_invariant_model_unavailable_equals_rules_only() -> None:
    for hits in HIT_SETS.values():
        assert combine(hits, None) == combine(hits, ModelVote.SAFE)
