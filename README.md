# ScamSignal CM

An open-source scam signal for Mobile Money users in Cameroon.

Paste a suspicious SMS or WhatsApp message, say who sent it, and get a risk label
(**suspicious**, **unclear** or **no warning signs found**), the reasons behind it, and a safe next step.
It never blocks anything, never stores messages, and never says a message is safe.

Built at Hacktoberfest Hack Day Yaoundé 2026 (theme: *AI Belongs to Everyone*). Full spec: [docs/PRD.md](docs/PRD.md).

> Status: Hack Day build (Oct 31, 2026). Demo script: [docs/DEMO.md](docs/DEMO.md).

## How it works

1. A transparent rule engine (`rules/rules.json`) looks for warning patterns: PIN/OTP requests,
   "wrong transfer" refund requests, operator impersonation, urgency, links, and more.
   Operator warnings such as "never share your PIN" are masked first and do not trigger a warning.
2. An open model (Gemma 4, `gemma-4-26b-a4b-it`, via Google's Gemini API) gives one constrained label vote
   and a short explanation. It can only make a clean result more cautious (raise it to *unclear*).
   It can never lower a rule-based label and never produces *suspicious* on its own.
   If the API is unreachable, slow (> 8 s) or no key is set, the app returns the rules-only result.
3. The safe next step comes from human-written templates (`advice/advice.json`), never from the model.

## Setup

Requires Python 3.11+ (tested on 3.14).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
cp .env.example .env   # then put your key in .env (never commit it)
export GEMINI_API_KEY=...   # get one at https://aistudio.google.com/apikey; without it the app runs rules-only
```

## Run

```bash
set -a; source .env; set +a      # loads GEMINI_API_KEY; skip this to run rules-only
.venv/bin/uvicorn app.main:app --port 8000   # page + API on http://localhost:8000
curl -s localhost:8000/check -H 'Content-Type: application/json' \
  -d '{"text": "You won! Send your PIN to 6XX XXX XXX", "lang": "en", "sender_type": "number"}'
```

With a key, `GET /health` shows `"model_loaded": true` and responses have `"model_used": true`.
If the API fails, is slow (> 8 s) or no key is set, the app answers from the rules alone (`"model_used": false`).

API (PRD §8.2): `POST /check` with `text` (1–1000 chars), `lang` (`en`|`fr`|`pcm`), `sender_type`
(`named`|`number`|`unknown`); `GET /health`. Invalid input returns `422 {"error": "invalid input"}`
and the submitted text is never echoed back.

## Test

```bash
.venv/bin/pytest -q
```

## Evaluation

```bash
set -a; source .env; set +a
.venv/bin/python eval/eval.py               # rules-only and rules+model, writes eval/results.md
.venv/bin/python eval/eval.py --rules-only  # without the API
```

The test set (`eval/testset/{en,fr,pcm}.jsonl`) is written by humans only and committed before any rule
tuning; nobody tunes rules or prompts on it. The script prints Table A (label quality), Table B (what the
model adds, and its cost), confusion matrices per language and the misclassified ids, with the sample size
next to every number. The hosted model can't be pinned, so the report states the model id and run date.

**Results: pending.** There is no human-written test set yet. We chose not to let an AI write it: the same AI
assistant wrote the rules, so the numbers would be circular. No accuracy numbers are claimed until humans add
`eval/testset/{en,fr,pcm}.jsonl`.

## Limitations

- A warning signal, not proof. Always check in the official operator app.
- No measured accuracy yet (see Evaluation).
- **Known failure:** a real operator withdrawal approval ("…dial \*126# and enter your PIN") is flagged
  *suspicious*. The PIN rule can't tell "type your PIN into the official menu" from "send your PIN to someone".
- Pidgin support is experimental: Pidgin phrases, reasons and advice have not been reviewed by a native speaker.
- Advice texts are drafts and have not yet been reviewed by a human (see AI-tool disclosure).
- The AI part needs internet and the Gemini API; the hosted model can change without notice. Without it, the app
  answers from the rules alone.
- No rate limiting yet on `POST /check`.

## Privacy

- We do not store or log messages. They are processed in memory for one request only.
- **The message is sent to Google's Gemini API** to get the model's vote and explanation.
  Before sending, phone numbers and digit runs of 6+ are replaced with `[NUMBER]`.
  On the free tier, Google may use inputs to improve its products and human reviewers may read them.
- Rules run locally. Without an API key, nothing leaves the server.
- Do not paste PINs, OTP codes or personal details.

## Model attribution

- Model: Gemma 4 `gemma-4-26b-a4b-it`, hosted on the [Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
- Weights license: Apache-2.0 (separate from this repository's code license). Hosted use is under the
  [Gemini API terms](https://ai.google.dev/gemini-api/terms).
- A hosted model cannot be pinned to a revision; evaluation results state the model id and the run date.

## Contributing

Add rules for your language without touching Python: edit [`rules/rules.json`](rules/rules.json).

- `mask`: warning phrases real operators use ("never share", "ne communiquez jamais"). They are blanked out
  before rules run, so "never share your PIN" is not a hit, but "send your PIN" in the same message still is.
- `rules`: each has an `id`, a `severity` (`hard`: one hit means *suspicious*; `soft`: two different soft hits
  mean *suspicious*, one means *unclear*), regex `patterns`, and a `reason` in `en`, `fr` and `pcm`.
- Text is lowercased and accents are stripped before matching, so write patterns in lowercase; accents are optional.
- Rules run on every message whatever language is selected; the language only picks the reason text.
- A malformed rules file fails at startup with a clear error. Run `.venv/bin/pytest -q` after any change.
- Tune only on `eval/devset.jsonl`, never on the test set.

## AI-tool disclosure

AI coding assistants were used to build this project (GitHub Copilot): code, tests, rules, the draft advice
texts, the Pidgin text and docs/DEMO.md were AI-assisted, then reviewed by the team lead. The advice and Pidgin
texts still need a full human review. The evaluation test set must be written by humans only; no AI tool wrote,
read or tuned on it.

## Later

Ideas raised during the build that are out of today's scope (PRD §6). Not built today.
Format: `- idea (author)`.

- Local model (Qwen2.5-0.5B-Instruct or similar) behind the same `app/model.py` interface, so no message leaves the device (Mr. DCT)
- Rate limiting on `POST /check` before any public deployment, so the Gemini API quota can't be drained (build agent)

## License

Code: [Apache-2.0](LICENSE). The model has its own license (see Model attribution).
