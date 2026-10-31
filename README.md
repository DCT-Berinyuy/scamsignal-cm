# ScamSignal CM

An open-source scam signal for Mobile Money users in Cameroon.

Paste a suspicious SMS or WhatsApp message, say who sent it, and get a risk label
(**suspicious**, **unclear** or **no warning signs found**), the reasons behind it, and a safe next step.
It never blocks anything, never stores messages, and never says a message is safe.

Built at Hacktoberfest Hack Day Yaoundé 2026 (theme: *AI Belongs to Everyone*). Full spec: [docs/PRD.md](docs/PRD.md).

> Status: work in progress. Sections marked _TBD_ are filled in as the build progresses.

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

_TBD_

## Test

```bash
.venv/bin/pytest -q
```

## Evaluation

_TBD_: `python eval/eval.py` reproduces every number in this section (Tables A and B, PRD §10).

## Limitations

_TBD_

- A warning signal, not proof. Always check in the official operator app.
- Pidgin support is experimental; its accuracy is reported separately.

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

_TBD_: how to add rule patterns and warning (mask) phrases in `rules/rules.json` without touching Python.

## AI-tool disclosure

AI coding assistants were used to build this project (GitHub Copilot). All rules, advice templates and
evaluation results are reviewed by the human team. The evaluation test set is written by humans only;
no AI tool wrote, read or tuned on it.

## Later

Ideas raised during the build that are out of today's scope (PRD §6). Not built today.
Format: `- idea (author)`.

- Local model (Qwen2.5-0.5B-Instruct or similar) behind the same `app/model.py` interface, so no message leaves the device (Mr. DCT)

## License

Code: [Apache-2.0](LICENSE). The model has its own license (see Model attribution).
