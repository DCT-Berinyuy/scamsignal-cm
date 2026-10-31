"""Rule engine tests. Fixtures here are developer-written unit-test messages, NOT the evaluation test set."""

import json

import pytest

from app.rules import RulesConfigError, RuleSet, Severity, load_rules, normalize, parse_rules

RULES = load_rules()


def hit_ids(text: str, sender_type: str = "unknown") -> set[str]:
    return {h.id for h in RULES.check(text, sender_type)}


# --- PIN warning masking (PRD §8.3 required test) ---------------------------------------------

LEGIT_PIN_WARNINGS = {
    "en": [
        "Transaction successful. You have received 5,000 FCFA from JOHN D. New balance: 12,500 FCFA. "
        "Never share your PIN with anyone.",
        "Your Mobile Money PIN was changed successfully. Do not share your PIN or OTP with anyone, not even our staff.",
        "Reminder: do not give your PIN or password to anybody who calls you.",
    ],
    "fr": [
        "Transfert réussi. Vous avez reçu 10 000 FCFA de MARIE N. Nouveau solde : 15 000 FCFA. "
        "Ne communiquez jamais votre code secret.",
        "Votre code PIN a été modifié avec succès. Ne partagez jamais votre code PIN ou OTP, même avec nos agents.",
        "Rappel : ne communiquez pas votre code secret à un tiers.",
    ],
    "pcm": [
        "Money don enter: 5000 FCFA from PAUL T. No give anybody your PIN.",
        "Your PIN don change. No share your PIN or OTP with anybody.",
        "Neva give anybody your secret code o.",
    ],
}


@pytest.mark.parametrize(
    "lang,text", [(lang, t) for lang, texts in LEGIT_PIN_WARNINGS.items() for t in texts]
)
def test_legit_pin_warning_is_not_a_pin_request(lang: str, text: str) -> None:
    assert "pin_request" not in hit_ids(text, "named")


@pytest.mark.parametrize("lang", ["en", "fr", "pcm"])
def test_at_least_two_legit_pin_warnings_per_language(lang: str) -> None:
    assert len(LEGIT_PIN_WARNINGS[lang]) >= 2


@pytest.mark.parametrize(
    "text",
    [
        "Never share your PIN with anyone. To confirm your reward, send your PIN to 6XX XXX XXX.",
        "Ne communiquez jamais votre code secret. Pour valider, envoyez votre code secret au 6XX XXX XXX.",
        "No give anybody your PIN. But to collect your money, send your PIN for 6XX XXX XXX.",
    ],
)
def test_warning_plus_ask_is_still_a_pin_request(text: str) -> None:
    assert "pin_request" in hit_ids(text)


def test_masking_is_per_phrase_not_per_message() -> None:
    masked = RULES.masked("Never share your PIN. Enter your PIN here.")
    assert "never share" not in masked
    assert "enter your pin here" in masked


def test_word_pin_alone_is_not_a_hit() -> None:
    assert "pin_request" not in hit_ids("Your PIN was reset on 12/10.", "named")


# --- Other rules ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Hello, I sent 25 000 FCFA to your number by mistake. Please send it back to me.",
        "Bonjour, j'ai envoyé 20 000 FCFA sur votre numéro par erreur. Veuillez me les renvoyer svp.",
        "Abeg I send 10 000 for your number by mistake, send am back quick quick.",
    ],
)
def test_wrong_transfer_refund_is_hard(text: str) -> None:
    assert "wrong_transfer_refund" in hit_ids(text, "number")


def test_mistake_without_send_back_is_not_refund() -> None:
    assert "wrong_transfer_refund" not in hit_ids("Sorry, I called you by mistake.")


def test_operator_claim_from_number_is_hard_but_not_from_named_sender() -> None:
    text = "MTN MoMo Service: your account will be suspended. Dial 6XX XXX XXX."
    assert "operator_from_number" in hit_ids(text, "number")
    assert "operator_from_number" not in hit_ids(text, "named")
    assert "operator_from_number" not in hit_ids(text, "unknown")


@pytest.mark.parametrize(
    "rule_id,text",
    [
        ("urgency_threat", "Your account will be blocked within 24 hours."),
        ("urgency_threat", "Votre compte sera bloqué immédiatement."),
        ("reward_bait", "Congratulations! You are our lucky winner."),
        ("reward_bait", "Félicitations, vous avez gagné un cadeau."),
        ("reward_bait", "You don win 500 000 FCFA!"),
        ("link", "Claim it here: http://example-claim.xyz/win"),
        ("link", "Go to bit.ly/abc123 now"),
        ("agent_impersonation", "This is the customer care team."),
        ("agent_impersonation", "Je suis votre conseiller Orange."),
        ("call_request", "Call 6XX XXX XXX to receive your money."),
        ("call_request", "Appelez le 6XX XXX XXX pour valider."),
        ("call_request", "Dial *126*1*1*6XXXXXXXX*50000# to receive the money."),
        ("money_request", "Pay the registration fee of 2 000 FCFA to collect your prize."),
        ("money_request", "Veuillez envoyer 5 000 FCFA de frais de dossier."),
    ],
)
def test_soft_rules(rule_id: str, text: str) -> None:
    hits = RULES.check(text, "unknown")
    assert rule_id in {h.id for h in hits}
    assert next(h for h in hits if h.id == rule_id).severity == Severity.SOFT


@pytest.mark.parametrize(
    "text",
    [
        "Transfer of 5000 FCFA to JOHN D successful. New balance: 3000 FCFA.",
        "You have received 10 000 FCFA from MARIE N. Transaction ID: 1234.",
        "Dial *126# to check your balance.",
    ],
)
def test_normal_confirmations_have_no_hits(text: str) -> None:
    assert hit_ids(text, "named") == set()


def test_accents_are_optional() -> None:
    assert "urgency_threat" in hit_ids("Votre compte sera bloque immediatement.")
    assert normalize("Félicitations") == "felicitations"


def test_link_allowlist_skips_official_domain() -> None:
    data = json.loads(json.dumps(_minimal_rules()))
    data["rules"][0] = {
        "id": "link",
        "severity": "soft",
        "allow": ["official.cm"],
        "patterns": ["https?://\\S+"],
        "reason": {"en": "x", "fr": "x", "pcm": "x"},
    }
    rs = parse_rules(data)
    assert [h.id for h in rs.check("see https://www.official.cm/help", "named")] == []
    assert [h.id for h in rs.check("see https://official.cm.evil.xyz/", "named")] == ["link"]


# --- Reasons -------------------------------------------------------------------------------------


def test_reasons_hard_first_and_capped_at_four() -> None:
    text = (
        "Congratulations winner! Urgent: send your PIN and pay the 2000 FCFA fee. "
        "Call 6XX XXX XXX or visit bit.ly/x. I am your agent."
    )
    hits = RULES.check(text, "unknown")
    reasons = RULES.reasons(hits, "en")
    assert len(hits) > 4
    assert len(reasons) == 4
    assert reasons[0] == "asks you to give your PIN or secret code"


@pytest.mark.parametrize("lang", ["en", "fr", "pcm"])
def test_no_hits_reason_in_each_language(lang: str) -> None:
    assert RULES.reasons((), lang) == [RULES.no_hits_reason[lang]]


# --- Config validation (fail fast) ---------------------------------------------------------------


def _minimal_rules() -> dict:
    return {
        "mask": ["never share"],
        "no_hits_reason": {"en": "none", "fr": "aucun", "pcm": "nothing"},
        "rules": [
            {"id": "r1", "severity": "soft", "patterns": ["foo"], "reason": {"en": "a", "fr": "b", "pcm": "c"}}
        ],
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["rules"][0].update(severity="medium"),
        lambda d: d["rules"][0].update(patterns=["(unclosed"]),
        lambda d: d["rules"][0].update(patterns=[]),
        lambda d: d["rules"][0]["reason"].pop("pcm"),
        lambda d: d["rules"][0].update(sender_types=["robot"]),
        lambda d: d["rules"].append(dict(d["rules"][0])),
        lambda d: d.pop("no_hits_reason"),
    ],
)
def test_invalid_rules_fail_fast(mutate) -> None:
    data = _minimal_rules()
    mutate(data)
    with pytest.raises(RulesConfigError):
        parse_rules(data)


def test_repo_rules_file_loads() -> None:
    assert isinstance(RULES, RuleSet)
    assert {r.id for r in RULES.rules} >= {"pin_request", "wrong_transfer_refund", "operator_from_number"}
