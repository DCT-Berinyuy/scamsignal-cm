# Contributing to ScamSignal CM

Thanks for helping protect Mobile Money users in Cameroon. This guide lists who built the project and explains,
step by step, how to contribute code, rules, translations and test data.

## Contributors

| Contributor | Role | Main contributions |
|---|---|---|
| **Verla Berinyuy Ndey** ([@DCT-Berinyuy](https://github.com/DCT-Berinyuy)), Mr. DCT | Lead: backend, rules, model, evaluation | PRD, FastAPI API, rule engine and masking, decision table, Gemma model step, output filter, privacy tests, eval script, deployment |
| **[@atarhbekatoh-star](https://github.com/atarhbekatoh-star)** | Frontend and docs | Web page (`static/`): paste box, language and sender buttons, result card, example buttons, limitations |

Built at **Hacktoberfest Hack Day Yaoundé 2026** (theme: *AI Belongs to Everyone*).
AI coding assistants (GitHub Copilot) were used during the build; see the AI-tool disclosure in the [README](README.md).

Want to see your name here? Open a pull request and add yourself to this table in the same PR.

---

## Ways to contribute

| You know… | You can… | Where |
|---|---|---|
| French, English or Cameroonian Pidgin | Add scam patterns and warning phrases for your language, review Pidgin text | `rules/rules.json`, `advice/advice.json` |
| How real operator SMS look | Verify official sender names and message formats (see open questions below) | Issues |
| Python | Fix false alarms, add tests, improve the API | `app/`, `tests/` |
| HTML/CSS/JS | Improve accessibility and the mobile layout | `static/` |
| Nothing technical | Write test messages (humans only, see below), report wrong results | `eval/testset/`, Issues |

---

## Development setup

Requires Python 3.11+ (tested on 3.14) and Git.

```bash
git clone https://github.com/DCT-Berinyuy/scamsignal-cm.git
cd scamsignal-cm
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pytest -q                          # all tests must pass, fully offline
.venv/bin/uvicorn app.main:app --port 8000   # http://localhost:8000 (rules-only)
```

To use the AI model locally, get a free key at https://aistudio.google.com/apikey, then:

```bash
cp .env.example .env      # put GEMINI_API_KEY=... in .env (never commit it)
set -a; source .env; set +a
.venv/bin/uvicorn app.main:app --port 8000   # /health shows "model_loaded": true
```

Tests never call the real API: the key is removed from the environment during tests.

## Project layout

```
app/
  config.py    APP_NAME (the only place the name lives), limits, model id
  rules.py     normalize → mask warning phrases → match rules/rules.json
  combine.py   decision table (rules first, the model can only add caution)
  model.py     Gemma on the Gemini API: redaction, prompt, strict reply parsing, 8 s timeout
  filter.py    rejects unsafe model explanations (digits, links, "safe", PIN asks)
  advice.py    human-written advice and explanation templates
  main.py      FastAPI: POST /check, GET /health, serves static/
rules/rules.json     scam patterns, warning phrases, reasons in en/fr/pcm
advice/advice.json   safe next steps in en/fr/pcm
static/              the web page (plain HTML/JS/CSS, no build step)
eval/eval.py         evaluation (Tables A and B); eval/testset/ is human-written
tests/               pytest suite
docs/                PRD.md (spec), DEMO.md (demo script)
```

Request flow: `text → rules → model → filter → combine → response`. Nothing is stored.

---

## Adding or fixing rules (no Python needed)

Everything is in [`rules/rules.json`](rules/rules.json).

1. **Warning phrases (`mask`)**: phrases real operators use, like "never share" or "ne communiquez jamais".
   They are removed before rules run, so "Never share your PIN" is not flagged. Removal is per phrase:
   "Never share your PIN… send your PIN to 6XX XXX XXX" is still caught.
2. **Rules (`rules`)**: each rule has:
   - `id`: unique, snake_case
   - `severity`: `hard` (one hit means *suspicious*) or `soft` (two different soft hits mean *suspicious*,
     one means *unclear*)
   - `patterns`: regular expressions
   - `reason`: a short phrase in `en`, `fr` and `pcm`
   - optional `sender_types` (for example only `number`) and `allow` (official domains for the link rule)
3. Text is lowercased and accents are removed before matching. Write patterns in lowercase; accents are optional.
4. Rules run on every message, whatever language the user picked.
5. Add a test for your change in `tests/test_rules.py`: one message that must be caught and one legitimate
   message that must not be. A malformed rules file fails at startup and in the tests.
6. Every new rule id needs an advice entry in `advice/advice.json` (a test checks this).

Example: adding a French urgency phrase.

```json
"\\b(urgent|urgence|immediatement|derniere chance|votre compte expire)\\b"
```

## Editing advice

[`advice/advice.json`](advice/advice.json) holds the safe next step for each rule, in `en`, `fr` and `pcm`.

- Point people to the **official app** only.
- **No phone numbers, USSD codes or digits** until a human has verified them (a test enforces this).
- Never say a message is "safe". Keep each entry to 1–3 short sentences.
- If `pcm` is missing, English is shown.

---

## Non-negotiable rules

These protect users. A pull request that breaks them will not be merged.

1. **The model can only add caution.** It may raise a message with no rule hits to *unclear*. It can never lower a
   rule label, and it can never produce *suspicious* on its own (`app/combine.py`, `tests/test_combine.py`).
2. **Privacy.** Never log, store or echo the submitted text, in logs, errors or analytics. The canary tests in
   `tests/test_privacy.py` must pass. Phone numbers and codes are redacted before the model call.
3. **Never say "safe".** Labels are *suspicious*, *unclear* and *no warning signs found*.
4. **Advice is human-written**, never generated by the model.
5. **The test set is written by humans only.** No AI tool may write, edit or tune on `eval/testset/`. People who
   write rules should not write test messages. Tune rules only on `eval/devset.jsonl`.
6. **No secrets in the repo.** Keys live in `.env` (gitignored) or the hosting platform's settings.
7. **No new dependencies** without a short justification in the PR.

## Writing test-set messages (humans only)

Files: `eval/testset/en.jsonl`, `fr.jsonl`, `pcm.jsonl`, one JSON object per line:

```json
{"id": "fr-07", "lang": "fr", "text": "…", "sender_type": "number", "expected": "suspicious", "scam_type": "wrong_transfer", "paraphrased": false, "author": "your-github-handle"}
```

- `sender_type`: `named`, `number` or `unknown`. `expected`: `suspicious`, `unclear` or `no_warning_signs`.
- Per language: 10 scams, 6 legitimate messages (at least 2 containing a PIN warning), and 2–3 paraphrased scams
  that avoid obvious keywords (`"paraphrased": true`).
- Messages must be synthetic: no real private messages, and fake numbers like `6XX XXX XXX`.
- Then run `python eval/eval.py` to produce `eval/results.md`.

---

## Pull request workflow

1. Open or pick an issue, then create a branch: `feat/…`, `fix/…`, `docs/…`, `test/…` or `chore/…`.
2. Keep PRs small and focused. Use [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`.
3. Before pushing: `.venv/bin/pytest -q` must be green with no warnings.
4. In the PR description: what changed, why, and how you tested it (paste example messages and results).
5. A maintainer reviews and merges. Be kind; this project is for everyone.

## Good first contributions

- Native-speaker review of the Pidgin warning phrases, reasons and advice.
- Fix the known false alarm: real withdrawal approvals that say "enter your PIN" in the official menu.
- Catch "MTN MoMo here" style operator claims sent from a phone number.
- Verify official sender names (MTN MoMo, Orange Money) to add to the link and sender rules.
- Add rate limiting to `POST /check`.
- Write human test-set messages so the README can report real accuracy numbers.

Questions? Open an issue on GitHub.
