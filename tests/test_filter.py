"""Output filter (PRD §8.4): the model's "why" is rejected for digits, URLs, phones, safety words or PIN asks."""

import pytest

from app.filter import MAX_WHY_CHARS, clean_why, is_rejected


@pytest.mark.parametrize(
    "why",
    [
        "This message pretends to be from your operator and pushes you to act fast.",
        "Ce message prétend venir de votre opérateur et vous presse d'agir.",
        "Dis message di pretend say na your operator, e di rush you.",
        "Le message vous demande de cliquer sur un lien inconnu.",  # "sur" (on) is not "sûr" (safe)
        "Never share your PIN with anyone who contacts you.",  # a warning, not an ask
    ],
)
def test_accepts_plain_explanations(why: str) -> None:
    assert clean_why(why) == why


@pytest.mark.parametrize(
    "why",
    [
        "Pay the 2000 FCFA fee to unlock it.",
        "Call 6XX XXX XXX to confirm.",
        "Visit https://example.com for details.",
        "Go to bit.ly/abc to check.",
        "Check www.example.org first.",
        "This message looks safe.",
        "This is a legit transaction.",
        "It seems genuine.",
        "Ce message est sûr.",
        "Ce message est sans danger.",
        "Le message semble authentique.",
        "To be sure, send your PIN to the agent.",
        "Confirmez votre code secret pour continuer.",
        "Reach them at +237 now.",
    ],
)
def test_rejects_unsafe_explanations(why: str) -> None:
    assert is_rejected(why)
    assert clean_why(why) is None


def test_keeps_at_most_two_sentences() -> None:
    raw = "First sentence here. Second one too! Third should go. Fourth as well."
    assert clean_why(raw) == "First sentence here. Second one too!"


def test_collapses_whitespace_and_handles_empty() -> None:
    assert clean_why("  It  pushes\nyou to hurry.  ") == "It pushes you to hurry."
    assert clean_why("") is None
    assert clean_why(None) is None
    assert clean_why("   ") is None


def test_rejects_overlong_text() -> None:
    assert clean_why("a" * (MAX_WHY_CHARS + 1)) is None
