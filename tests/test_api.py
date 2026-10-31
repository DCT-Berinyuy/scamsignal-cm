"""API contract tests (PRD §8.2). Rules-only: model_used is always false at this step."""

import pytest

from app.advice import AdviceConfigError, parse_advice
from app.config import APP_NAME, MAX_TEXT_LEN
from app.rules import RuleHit, Severity, default_rules

SCAM_EN = "Congratulations! You won 500 000 FCFA. To confirm, send your PIN to 6XX XXX XXX."
LEGIT_EN = "Transfer of 5000 FCFA to JOHN D successful. New balance: 3000 FCFA. Never share your PIN."


def post(client, text: str = SCAM_EN, lang: str = "en", sender_type: str = "number"):
    return client.post("/check", json={"text": text, "lang": lang, "sender_type": sender_type})


def test_health(client) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "model_loaded": False, "app_name": APP_NAME}


def test_check_response_shape(client) -> None:
    res = post(client)
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"label", "reasons", "rule_hits", "why", "advice", "model_used", "lang"}
    assert body["label"] == "suspicious"
    assert body["model_used"] is False
    assert body["lang"] == "en"
    assert {"id": "pin_request", "severity": "hard"} in body["rule_hits"]
    assert 1 <= len(body["reasons"]) <= 4
    assert body["reasons"][0] == "asks you to give your PIN or secret code"
    assert body["why"] and body["advice"]


def test_legit_message_has_no_warning_signs(client) -> None:
    body = post(client, LEGIT_EN, sender_type="named").json()
    assert body["label"] == "no_warning_signs"
    assert body["rule_hits"] == []
    assert body["reasons"] == ["No known warning patterns matched."]


def test_one_soft_hit_is_unclear(client) -> None:
    body = post(client, "Your account will be blocked within 24 hours.", sender_type="named").json()
    assert body["label"] == "unclear"


@pytest.mark.parametrize("lang", ["en", "fr", "pcm"])
def test_reasons_and_advice_follow_language(client, lang) -> None:
    rules = default_rules()
    body = post(client, lang=lang).json()
    assert body["lang"] == lang
    assert body["reasons"][0] == next(r for r in rules.rules if r.id == "pin_request").reason[lang]


def test_advice_comes_from_highest_severity_hit(client) -> None:
    body = post(client).json()
    soft_first = post(client, "Congratulations winner! Click bit.ly/x", sender_type="named").json()
    assert body["advice"].startswith("Do not send your PIN")
    assert soft_first["advice"] != body["advice"]


def test_never_says_safe(client) -> None:
    body = post(client, LEGIT_EN, sender_type="named").json()
    assert "safe" not in (body["why"] + body["advice"] + " ".join(body["reasons"])).lower()


def test_max_length_is_accepted(client) -> None:
    assert post(client, "a" * MAX_TEXT_LEN).status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "", "lang": "en", "sender_type": "named"},
        {"text": "   \n ", "lang": "en", "sender_type": "named"},
        {"text": "a" * (MAX_TEXT_LEN + 1), "lang": "en", "sender_type": "named"},
        {"text": "hello", "lang": "de", "sender_type": "named"},
        {"text": "hello", "lang": "en", "sender_type": "friend"},
        {"text": "hello", "lang": "en"},
        {"text": "hello", "lang": "en", "sender_type": "named", "extra": 1},
        {"text": 123, "lang": "en", "sender_type": "named"},
    ],
)
def test_invalid_input_is_422_without_details(client, payload) -> None:
    res = client.post("/check", json=payload)
    assert res.status_code == 422
    assert res.json() == {"error": "invalid input"}


def test_malformed_json_is_422(client) -> None:
    res = client.post("/check", content=b"{not json", headers={"Content-Type": "application/json"})
    assert res.status_code == 422
    assert res.json() == {"error": "invalid input"}


def test_docs_are_disabled(client) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_static_mount_serves_page_without_shadowing_api(client, tmp_path, monkeypatch) -> None:
    from starlette.staticfiles import StaticFiles

    from app.main import app

    (tmp_path / "index.html").write_text("<title>page</title>")
    mount = next(r for r in app.routes if getattr(r, "name", "") == "static")
    monkeypatch.setattr(mount, "app", StaticFiles(directory=tmp_path, html=True))
    assert "<title>page</title>" in client.get("/").text
    assert client.get("/health").json()["status"] == "ok"
    assert client.post("/check", json={"text": "hi", "lang": "en", "sender_type": "named"}).status_code == 200


# --- Advice file -----------------------------------------------------------------------------


def test_repo_advice_covers_every_rule() -> None:
    from app.advice import default_advice

    book = default_advice()
    for rule in default_rules().rules:
        assert rule.id in book.entries, f"no advice for {rule.id}"


def test_advice_has_no_phone_numbers_or_ussd() -> None:
    import re

    from app.advice import default_advice

    book = default_advice()
    texts = [t for e in book.entries.values() for t in e.values()]
    assert not any(re.search(r"\d|\*\d|#", t) for t in texts)


def test_pidgin_advice_falls_back_to_english() -> None:
    book = parse_advice(
        {
            "why_template": {"hits": {"en": "W: {reasons}", "fr": "F: {reasons}"}, "no_hits": {"en": "n", "fr": "n"}},
            "advice": {"no_hits": {"en": "EN", "fr": "FR"}, "default": {"en": "D", "fr": "D"}},
        }
    )
    assert book.advice((), "pcm") == "EN"
    assert book.why_template(["a", "b"], True, "pcm") == "W: a; b"
    assert book.advice((RuleHit("unknown_rule", Severity.SOFT),), "fr") == "D"


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"advice": {"default": {"en": "x", "fr": "x"}}, "why_template": {}},
        {
            "advice": {"no_hits": {"en": "x"}, "default": {"en": "x", "fr": "x"}},
            "why_template": {"hits": {"en": "{reasons}", "fr": "{reasons}"}, "no_hits": {"en": "n", "fr": "n"}},
        },
        {
            "advice": {"no_hits": {"en": "x", "fr": "x"}, "default": {"en": "x", "fr": "x"}},
            "why_template": {"hits": {"en": "no placeholder", "fr": "{reasons}"}, "no_hits": {"en": "n", "fr": "n"}},
        },
    ],
)
def test_invalid_advice_fails_fast(data) -> None:
    with pytest.raises(AdviceConfigError):
        parse_advice(data)


# --- With a model (fake, no network) ---------------------------------------------------------

from app.combine import ModelVote  # noqa: E402
from app.model import ModelResult  # noqa: E402

PARAPHRASED = "Hi, this is your uncle on a new line. Kindly help me with something small."


class FakeModel:
    def __init__(self, result: ModelResult | None) -> None:
        self.result = result
        self.calls: list[tuple] = []
        self.healthy = result is not None

    async def assess(self, text, lang, sender_type, rule_reasons):
        self.calls.append((text, lang, sender_type, list(rule_reasons)))
        return self.result


@pytest.fixture()
def use_model(client):
    def _use(result: ModelResult | None) -> FakeModel:
        fake = FakeModel(result)
        client.app.state.model = fake
        return fake

    return _use


def test_model_raises_clean_message_to_unclear(client, use_model) -> None:
    use_model(ModelResult(ModelVote.UNCLEAR, "It asks for help from an unknown new line."))
    body = post(client, PARAPHRASED, sender_type="unknown").json()
    assert body["label"] == "unclear"
    assert body["model_used"] is True
    assert body["rule_hits"] == []
    assert body["why"] == "It asks for help from an unknown new line."


def test_model_alone_never_produces_suspicious(client, use_model) -> None:
    use_model(ModelResult(ModelVote.SUSPICIOUS, "Looks like a scam."))
    assert post(client, PARAPHRASED, sender_type="unknown").json()["label"] == "unclear"


def test_model_cannot_lower_a_rule_label(client, use_model) -> None:
    use_model(ModelResult(ModelVote.SAFE, "Looks ordinary."))
    body = post(client).json()  # hard PIN request
    assert body["label"] == "suspicious"
    assert body["model_used"] is True


def test_rejected_why_falls_back_to_template(client, use_model) -> None:
    use_model(ModelResult(ModelVote.UNCLEAR, "Call 6XX XXX XXX, this message is safe."))
    body = post(client).json()
    assert body["why"].startswith("Warning signs found:")
    assert body["model_used"] is True


def test_model_unavailable_is_rules_only(client, use_model) -> None:
    use_model(None)
    body = post(client, PARAPHRASED, sender_type="unknown").json()
    assert body["label"] == "no_warning_signs"
    assert body["model_used"] is False
    assert client.get("/health").json()["model_loaded"] is False


def test_model_gets_english_rule_reasons_and_language(client, use_model) -> None:
    fake = use_model(ModelResult(ModelVote.SUSPICIOUS, None))
    post(client, lang="fr")
    _, lang, sender_type, reasons = fake.calls[0]
    assert (lang, sender_type) == ("fr", "number")
    assert reasons[0] == "asks you to give your PIN or secret code"


def test_health_reports_model_loaded(client, use_model) -> None:
    use_model(ModelResult(ModelVote.SAFE, None))
    assert client.get("/health").json()["model_loaded"] is True
