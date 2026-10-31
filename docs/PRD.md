PRD v3: ScamSignal CM (working title)

An open-source scam signal for Mobile Money users in Cameroon

Hacktoberfest Hack Day Yaoundé 2026 · Theme: AI Belongs to Everyone · Oct 31, 2026
Author: Mr. DCT (Verla Berinyuy Ndey), with the Hack Day team
Status: v3.1 (3-member PR workflow), replaces v2. Scope freezes at Checkpoint 2 (§14).
Repo: scamsignal-cm · License: Apache-2.0

Team rule: If it is not in §6 "Must have", it waits. New ideas go into the "Later" list in the README, not into the code.



0. What changed (read this first)

v2 → v3

Area
v2
v3
Name
MoMo Shield ("MoMo" is an MTN brand)
ScamSignal CM, defined once in app/config.py (APP_NAME) so it can change in one place
PIN/OTP rule
Matched the word "PIN", so real operator warnings like "never share your PIN" were flagged
Matches only the ask (send/enter/confirm/give/share + PIN/OTP/secret code). Warning phrasing is masked first and is not a hit. Unit-tested.
Model's job
Not measured
6–8 paraphrased scams (no rule keywords) in the test set. The "Why AI" table reports how many the rules miss and the model raises to unclear.
"Why AI" metric
Precision/recall rules-only vs rules+model (always identical under the invariants)
"Flagged" = suspicious or unclear, plus the cost: legitimate messages the model wrongly raised to unclear (§10)
Under time pressure
Decided on the spot
Pre-decided cut order (§6)
License
Apache-2.0 or MIT
Apache-2.0
Team
4 roles
3 members, all contribute via PRs; lead takes the heavy path (§14)
Test set file
eval/testset.jsonl
eval/testset/{en,fr,pcm}.jsonl, one per language, so two people can open PRs without conflicts
Build order
Not specified
Specified in §14

v1 → v2 (summary)

Area
v1
v2
Safe label
likely safe
no warning signs found (we never say "safe")
Label logic
"model can nudge", "disagree → unclear"
One-directional decision table (§7). The model can make the label more cautious, never less.
Advice
Written by the model
Human-written templates per rule and language. The model writes only the short "why".
Language
Auto-detect
Manual EN / FR / Pidgin buttons
New input
—
Sender type: named sender / phone number / don't know
Evaluation
Precision/recall, vague
Locked test set, confusion matrix per language, rules-only vs rules+model
Privacy
"Not stored" (untestable)
Canary log test, no input echoed in errors
Frontend
HTML/JS or SvelteKit
Plain HTML/JS served by FastAPI (one deploy, no build step, no CORS)
Distribution
Paste only
Paste + share result. Stretch: Android "Share to ScamSignal CM" (PWA).



1. Summary

ScamSignal CM is a free, open-source web tool. A person pastes a suspicious SMS or WhatsApp message, says who sent it, and gets:

a risk label: suspicious, unclear or no warning signs found,
the plain-language reasons behind it,
a safe next step.

It uses a transparent rule layer and a small open-source AI model (Qwen2.5-0.5B-Instruct). It supports English and French. Pidgin is experimental, and its accuracy is reported separately. It never blocks anything, never stores messages and never says a message is safe.

2. Problem

Mobile Money is how many Cameroonians send, receive and save money. Scammers send fake reward messages, fake "wrong transfer" refund requests, fake agent or support messages, and requests for PINs and OTP codes. Victims have no quick way to check a message, and existing spam filters are mostly English-only and don't explain their decisions.

What we have not verified: We have no citable statistics on scam frequency in Cameroon. The pitch uses a quick on-site check (ask people in the room), not invented numbers.

3. Target community

Everyday Mobile Money users in Cameroon, especially students and small traders, who receive scam messages in English, French and Pidgin.

Submission category: Finance / financial inclusion. If that's not on the form, use General public / community safety.
Pitch line: "A free, open-source scam checker that explains why a message is risky and tells you the safe next step, in the languages people actually use."

4. Goals and non-goals

Goals (today)

Working end-to-end demo: paste a message → label, reasons, why, safe advice.
Public repo with an OSI-approved license, a clear README and reproducible evaluation results.
A measured answer to "why AI?": a rules-only vs rules+model comparison table.
Performance: p95 response ≤ 10 s on the demo laptop. The rules-only fallback returns in < 1 s.
Two-minute demo with EN, FR and Pidgin examples, a legitimate message, and one honest failure.

Non-goals

No automatic blocking, ever (not today, not on the roadmap).
No server-side inbox access or SMS interception. On-device, opt-in scanning is future work (§18).
No claim of guaranteed safety or high accuracy.
No native mobile app, user accounts or database today.
No fine-tuning today.
No datasets with unclear or restrictive licenses.
No model swap during the build (see §9: larger Qwen sizes have different licenses).

5. Users and stories

Student: "I got a message saying I won a reward and must confirm my PIN. Is it real?"
Small trader: "A message says money was sent to me by mistake and asks me to send it back. What should I do?"
Family helper: "My parent forwarded me a strange message in Pidgin. I want a second opinion I can send back to them."

6. Scope

Must have (demo depends on these)

Paste box (max 1000 characters).
Language buttons: EN / FR / Pidgin (manual, default EN).
Sender question: "Who sent it?" Named sender (e.g. MobileMoney, OrangeMoney) / Phone number / Don't know.
Rule engine reading rules/rules.json (§8.3).
Decision table (§7), with unit tests.
Model step: one constrained label vote + a short "why" (≤ 2 sentences), with an output filter and template fallback.
Advice templates in EN / FR / Pidgin (advice/advice.json), written by humans.
Result card: label, reasons, why, safe next step, reminder: "Verify in the official app. Never share your PIN or OTP."
Built-in example message buttons (for the demo).
About/limitations section.
eval/eval.py reproducing all README numbers with one command.

Should have (only after all Must haves work)

"Share this result" button (navigator.share, fallback: copy text). ~30 min.

Stretch (only if Checkpoint 2 passes with time left)

Installable PWA + Web Share Target so Android users can pick "Share → ScamSignal CM" from the SMS app or WhatsApp. ~1.5–2 h. Requires HTTPS and Chrome on Android. Test on the actual demo phone.

Cut (do not build today)

USSD, WhatsApp bot, Telegram bot, browser extension, iOS anything, native Flutter app, SMS reading, language auto-detect, feedback storage, analytics, model upgrades, the UCI dataset (use only if all else is done).

Cut order if we run behind (decided now, not under pressure)

Cut in this order, one step at a time, only as far as needed:

Per-language confusion matrices. Keep one overall table.
Pidgin advice templates. Fall back to English advice for Pidgin and say so in the UI and README.
The share button.

Never cut: the test set, the decision-table unit tests (including the PIN-warning test), the privacy canary test, the backup demo video.

7. Decision logic and output spec

7.1 Rule severities

Hard (one hit is enough):
asks the user to hand over a PIN, OTP, password or secret code: an ask verb (send, enter, confirm, give, share, type, dial, envoyez, entrez, confirmez, donnez, communiquez, tapez, Pidgin send, give, put) near PIN/OTP/secret code/password. The word "PIN" alone is not a hit.
asks to send money back for a "wrong transfer" or "mistake";
claims to be MTN/Orange/an operator and sender type is "Phone number".
Soft (signals that add up): urgency or threats, reward/prize bait, any link, impersonation of an agent or support, request to call or dial a number, request to send money (non-refund).

Warning phrasing is not a hit. Real operator messages often say "never share your PIN". Before the ask patterns run, the engine masks warning phrases: "never share", "do not share", "don't give", "ne communiquez jamais", "ne partagez jamais", "ne donnez jamais", Pidgin "no give anybody", "no share", "neva give" (Pidgin phrasing to be confirmed by a native speaker, §16).
Masking is per phrase, not per message. A scam that adds "never share your PIN" and then says "send your PIN to confirm" is still caught, because only the warning phrase is removed.

7.2 Decision table (in this order)

#
Condition
Label
1
Any hard hit
suspicious
2
≥ 2 soft hits
suspicious
3
Exactly 1 soft hit
unclear
4
0 hits and model votes suspicious or unclear
unclear
5
0 hits and model votes safe, or model unavailable
no warning signs found

Invariants (must be unit-tested):

The model can never lower a label set by rules (rows 1–3 ignore the model vote).
The model alone can never produce suspicious (0.5B is too weak to be trusted on its own).
Model timeout or error → rules-only result, model_used: false.

7.3 Output fields

Label: one of the three above.
Reasons: 1–4 short items from rule hits, in the chosen language (e.g. "asks for your PIN", "creates urgency"). With 0 hits: "No known warning patterns matched."
Why: ≤ 2 sentences from the model, in the chosen language, after the output filter (§8.4). If the filter rejects it, use a template built from the reasons.
Safe next step: from advice/advice.json, selected by the highest-severity rule hit. Never model-generated.
Confidence note (always shown): "This is a warning signal, not proof. Check in the official app."

8. Architecture

8.1 Components

Browser (static HTML/JS, served by FastAPI)
  │  POST /check
  ▼
FastAPI
  ├─ config.py    → APP_NAME = "ScamSignal CM", model id + pinned revision, limits
  ├─ rules.py     → mask warning phrases, then rule hits (from rules/rules.json)
  ├─ model.py     → label vote + "why" (Qwen2.5-0.5B, 8 s timeout)
  ├─ combine.py   → decision table §7.2
  ├─ filter.py    → output filter §8.4
  └─ advice.json  → safe next step templates

Flow: text → rules → model (text + rule hits) → filter → combine → response. Nothing is stored.

8.2 API contract

POST /check

{
  "text": "string, 1–1000 chars",
  "lang": "en | fr | pcm",
  "sender_type": "named | number | unknown"
}

Response 200:

{
  "label": "suspicious | unclear | no_warning_signs",
  "reasons": ["asks for your PIN", "creates urgency"],
  "rule_hits": [{ "id": "pin_request", "severity": "hard" }],
  "why": "string",
  "advice": "string",
  "model_used": true,
  "lang": "en"
}

Errors: invalid or too-long input → 422 with { "error": "invalid input" }. The submitted text is never echoed back (override FastAPI's default validation handler, which includes the input).

GET /health → { "status": "ok", "model_loaded": true|false }

8.3 Rules file format (rules/rules.json)

{
  "mask": [
    "never share", "do not share", "don't share", "don't give", "never give",
    "ne communiquez jamais", "ne partagez jamais", "ne donnez jamais",
    "no give anybody", "no share", "neva give"
  ],
  "rules": [
    {
      "id": "pin_request",
      "severity": "hard",
      "lang": ["en", "fr", "pcm"],
      "patterns": [
        "\\b(send|enter|confirm|give|share|type|dial|put)\\b.{0,30}\\b(pin|otp|secret code|password)\\b",
        "\\b(envoyez|entrez|confirmez|donnez|communiquez|tapez|saisissez)\\b.{0,30}\\b(code secret|code pin|pin|otp|mot de passe)\\b"
      ],
      "reason": {
        "en": "asks you to give your PIN or secret code",
        "fr": "vous demande de donner votre code PIN ou code secret",
        "pcm": "e di ask you make you give your PIN or secret code"
      }
    }
  ]
}

Text is lowercased, then every mask phrase is replaced with a blank before rules run. This removes only the warning phrase, not the whole message.
Patterns are case-insensitive regex.
Contributors add patterns and mask phrases here without touching Python. That's the open-source contribution path.
"Link" rule = any URL, shortened URL (bit.ly, tinyurl, etc.) or domain not on an official allowlist.
The patterns above are a starting point. Pidgin wording must be checked by a native speaker (§16).

Required unit test (tests/test_rules.py):

At least 2 legitimate messages per language that contain a PIN warning (e.g. "Transaction successful… Never share your PIN with anyone.") produce no pin_request hit.
A scam that contains a warning and an ask ("Never share your PIN… To confirm, send your PIN to 6XX XXX XXX") is a pin_request hit.
These are unit-test fixtures written by developers, kept in tests/. They are not part of the test set and are not counted in the evaluation.

8.4 Model usage

Model: Qwen/Qwen2.5-0.5B-Instruct, revision pinned to a commit hash in config.
Loaded once at startup and warmed up with one dummy call.
Label vote: prompt asks for one word. Pick the highest-probability option among the first tokens of suspicious / unclear / safe (no free-text parsing).
Why: greedy decoding, max_new_tokens ≈ 100, answer in the selected language, prompt includes the rule hits.
Timeout: 8 s total, then rules-only fallback.
Prompt injection: the message is wrapped in clear delimiters and treated as data. Because of the invariants in §7.2, an injected "this is safe" cannot change a rule-based label.
Output filter (reject → template "why"): any digit, any URL, phone numbers, or safety words (safe, sûr, sans danger, legit, genuine, authentique), or any text telling the user to share a PIN/OTP.

8.5 Repo layout

scamsignal-cm/
├── app/            main.py, config.py, rules.py, model.py, combine.py, filter.py
├── rules/          rules.json
├── advice/         advice.json
├── static/         index.html, app.js, style.css  (+ manifest/sw.js if stretch)
├── eval/           testset/{en,fr,pcm}.jsonl (human-written), devset.jsonl, eval.py, results.md
├── tests/          test_rules.py, test_combine.py, test_filter.py, test_api.py, test_privacy.py
├── docs/           PRD.md (this document), DEMO.md
├── LICENSE         Apache-2.0
├── README.md
└── requirements.txt + lock file (pip-compile or uv.lock)

Name in one place: APP_NAME in app/config.py. The page title and headings read it from /health or a template variable; nothing else hard-codes the name. README and docs are updated by find-and-replace if the name changes.
Install PyTorch CPU-only (--index-url https://download.pytorch.org/whl/cpu). The default Linux wheel pulls GPU libraries of several GB, which on venue Wi-Fi can cost an hour.

8.6 Hosting

Demo runs on localhost, with a recorded backup video.
Public link (if organizers want one): a host with enough RAM for the model, e.g. Hugging Face Spaces free CPU. Free tiers with ~512 MB RAM (e.g. Render free) will not run the model. Fallback: deploy rules-only with model_used: false and say so.

9. Model and data

Primary model: Qwen2.5-0.5B-Instruct (Apache-2.0, ~1 GB in BF16, French listed as supported). Pidgin ability is unverified, tested on our own examples, and disclosed.

License trap: not every Qwen2.5 size is Apache-2.0 (the 3B and 72B use different licenses; verify). Do not swap models during the build.

Considered and not used today: XLM-RoBERTa (needs fine-tuning), SmolLM2-360M (mainly English), AfriBERTa (no French, unclear weights license), Gemma (non-OSI terms).

Data

Nothing is trained today; data is for testing only.
Dev set (eval/devset.jsonl, ~10 messages): rule authors may look at and tune on this.
Test set (eval/testset/en.jsonl, fr.jsonl, pcm.jsonl, 54–56 messages), written by members B and C (§14), never by the rule author and never by an AI agent:
3 languages × (10 scams + 6 legitimate) = 48. At least 2 of the 6 legitimate messages per language contain a PIN warning ("never share your PIN" style).
6–8 paraphrased scams across the 3 languages (at least 2 per language), written to avoid the rule keywords. Marked "paraphrased": true. They test what the model adds (§10).
Scams cover at least 4 types: fake reward, wrong-transfer refund, fake agent/support asking for PIN, account-suspension threat.
The test set is committed before the rules are tuned. The commit history proves it was not tuned on. Nobody tunes rules or prompts on it, and no AI agent generates it.
Each line: { "id", "lang", "text", "sender_type", "expected", "scam_type", "paraphrased", "author" }.
All messages are synthetic. No real private messages in the repo. No phone numbers that belong to real people (use 6XX XXX XXX-style fakes).
Not used: Cameroon Mobile Money survey data (all rights reserved). UCI SMS Spam Collection (CC BY 4.0) only as an optional false-positive check, with attribution, if time allows.

10. Evaluation

python eval/eval.py must reproduce every number in the README.

Run the test set twice: rules-only and rules+model.
Table A, label quality (rules+model): positive class = suspicious. Report precision and recall for suspicious and the count of false positives among legitimate messages. (Under the §7.2 invariants, rules-only and rules+model give the same suspicious labels, so one row is enough.)
Table B, "Why AI" (what the model adds): "flagged" = suspicious or unclear.
Report a 3×3 confusion matrix per language (EN, FR, Pidgin). First item in the cut order (§6): if cut, report one overall matrix.
State the sample size next to every number. With ~55 messages, results are indicative only.
Document at least one real failure in README and demo, with the reason.

Table B, "Why AI" (goes in README and the demo):


Rules only
Rules + model
n
Paraphrased scams flagged
_ / n
_ / n
6–8
Paraphrased scams the rules missed that the model raised to unclear (row 4)
—
_

Cost: legitimate messages wrongly raised to unclear by the model
—
_ / n
18

If the model catches none of the paraphrased scams, the README says so plainly. The model's other job, explaining in the user's language, is still shown in the demo. The invariants do not change: the model can only raise a clean message to unclear, never lower a rule label, and never produce suspicious alone.

11. Privacy, safety and ethics

Messages are processed in memory for the request only. Not stored, not logged.
Testable: tests/test_privacy.py sends a unique canary string, then asserts it is not in the captured logs and not in any error response.
No request-body logging, no debug mode, custom validation and exception handlers.
No third-party APIs. The model runs locally.
The page warns: "Do not paste PINs, OTP codes or personal details."
The tool never says "safe", never blocks, never contacts anyone.
Advice points only to the official operator app or verified official contacts (see §16). No unverified numbers or USSD codes in templates.
Messages may contain other people's names and numbers. Treat them as personal data (Cameroon's personal data protection law; verify the reference before citing it).
README includes limitations and an AI-tool disclosure (AI coding assistants used).

12. Open-source compliance checklist

Public GitHub repo that stays public after the event
LICENSE file (Apache-2.0 or MIT), detected by GitHub
README: what it is, setup, run, demo, evaluation, limitations, "Later" list, contributing (how to add rules)
Model attribution and license stated separately from the code license, with the pinned revision
Provenance and license for every dataset used
No secrets, API keys or private messages committed
Dependency lock file committed
Commit history shows work done during the event (test set committed before rule tuning)

13. Demo script (2:00)

Hook (15 s): a real story from the team or the room.
English (20 s): fake reward + PIN request, from a phone number → suspicious, reasons, why, advice.
French (15 s): fake agent asking to "return" a wrong transfer → suspicious.
Pidgin (15 s): short Pidgin scam, with an honest note on Pidgin quality.
Legitimate message (10 s): a normal confirmation from a named sender that includes "never share your PIN" → no warning signs found (note: not "safe", and the PIN warning didn't trigger it).
Honest failure (15 s): one message we get wrong, and why.
Why AI (15 s): a paraphrased scam the rules miss → the model raises it to unclear, then Table B (§10) with its cost. If the model caught none, say so.
Roadmap + close (15 s): the distribution ladder (§18), open source, "add rules for your language."

Backup: screen recording of the full demo, made at Checkpoint 2.

14. Team, PR workflow and timeline

Three members. Everyone contributes through pull requests. The lead takes the heavy path (backend, rules, model, evaluation) and merges.

14.1 Roles

Member
Role
Owns (files)
A: Mr. DCT (lead)
Backend, rules, model, eval, merges
app/, rules/rules.json, tests/, eval/eval.py, requirements*, LICENSE
B: ___
Frontend & docs
static/, advice/advice.json (EN + FR), README sections (setup, run, limitations, attribution, contributing), eval/testset/en.jsonl, submission form
C: ___
Test & demo
eval/testset/fr.jsonl, eval/testset/pcm.jsonl, eval/devset.jsonl, Pidgin advice text, Pidgin mask phrases review, docs/DEMO.md, backup video, §16 checks

Test-set rule: A (who writes rules and prompts) never writes or reads the test set before it is merged, and never tunes on it. B and C write it. Pidgin from a native speaker if possible. No AI agent writes or tunes on it.

One file per language (eval/testset/en.jsonl, fr.jsonl, pcm.jsonl) so B and C can open PRs in parallel without merge conflicts. Each file: 10 scams + 6 legitimate (≥ 2 with a PIN warning) + 2–3 paraphrased scams.

B can start the frontend immediately by building against a hard-coded sample response from §8.2. No need to wait for A's API.

14.2 PR plan

#
Owner
Branch
PR content
Depends on
0
A
main (direct, first commit only)
docs/PRD.md, LICENSE, .gitignore, empty README
—
1
A
chore/scaffold
§8.5 skeleton, app/config.py, requirements.txt + lock (CPU torch), README skeleton with AI-tool disclosure + "Later" section
0
2
C
test/testset-fr-pcm
eval/testset/fr.jsonl, pcm.jsonl
0
3
B
test/testset-en
eval/testset/en.jsonl
0
4
C
test/devset
eval/devset.jsonl (~10 messages A may tune on)
0
5
A
feat/rules-combine
rules.py, rules.json with masking, combine.py, test_rules.py, test_combine.py
1, 4
6
B
feat/static-page
Page, language + sender buttons, result card, example buttons, reminder, limitations
1
7
A
feat/check-api
/check + /health rules-only, 422 handler, test_api.py, test_privacy.py
5
8
B
feat/advice-en-fr
advice/advice.json EN + FR (no numbers or USSD codes until verified)
1
9
C
feat/advice-pcm
Pidgin advice entries + Pidgin mask/ask phrases review in rules.json
2, 5, 8
10
A
feat/model-filter
model.py, filter.py, test_filter.py (only after 7 + 6 work end to end)
6, 7
11
A
feat/eval
eval/eval.py, Tables A and B, eval/results.md
2, 3, 10
12
C
docs/demo
docs/DEMO.md script, failure write-up, link to backup video
11
13
B
docs/readme
README final: numbers from 11, setup/run, limitations, attribution
11
14
B
feat/share-button
Should-have, only if on time (cut order §6)
6

PR rules:

main is protected after PR 0: no direct pushes, PR required.
Small PRs, conventional commit titles (feat:, test:, docs:, chore:).
A reviews B and C. B or C reviews A (5-minute skim + approve; this also spreads knowledge of the code).
Test-set PRs (2, 3) merge before A runs any evaluation. A does not open those files before then.
Add the hacktoberfest topic to the repo so members' merged PRs can count (check current Hacktoberfest rules; today is the last day of October).

14.3 Timeline

Fill in absolute times once the schedule is confirmed.

Time
A (lead)
B
C
T+0 → T+15 min
PR 0, create GitHub repo, invite B + C, protect main, start model download
Clone, start PR 6 against the sample response
Start PR 2 (test set)
T+15 → Checkpoint 1 (~T+1h45)
PR 1, 5, 7 merged
PR 3 + PR 6 merged
PR 2 + PR 4 merged
→ Checkpoint 2 = SCOPE FREEZE (~T+3h)
PR 10 merged, end to end with model; PR 11 started
PR 8 merged
PR 9 merged; backup video recorded
Checkpoint 2 → final 45 min
PR 11 merged; fix worst failures
PR 14 only if green
PR 12
Final 45 min
Review + merge everything
PR 13; submission
Two full rehearsals with everyone

15. Risks and mitigations

Risk
Mitigation
Model slow or weak on Pidgin
Rules carry the label; model only votes (can't lower) and explains; disclose
Model download / RAM / hardware
Download the model at T+0; CPU-only torch; set dtype explicitly; rules-only fallback still demos
Test set not ready by Checkpoint 1 (~55 messages, 3 languages)
Split by language file between B and C; native speaker for Pidgin; PR in batches
PIN rule flags real operator warnings
Mask warning phrases before matching; unit test with ≥ 2 legit PIN-warning messages per language
Prompt injection in the pasted message
Delimiters + §7.2 invariants: the model can't lower a rule label
Model invents numbers, codes or "it's safe"
Advice is templated; output filter; template fallback
Circular evaluation
Test set written first by a non-rule author, committed before tuning
Data leaks via logs or error echo
Custom handlers, no body logging, canary test
False positives on real messages
18 legitimate test messages; precision reported; soft rules need ≥ 2 hits
Live demo failure (Wi-Fi, laptop)
Localhost, example buttons, backup video
Scope creep
Freeze at Checkpoint 2 is binding; ideas go to the "Later" list
Submission cutoff unclear
Ask the host now; submit a working version early, then update
License mistakes
§12 checklist; no model swap

16. Verify before demo (owner: C, unless noted)

Exact submission cutoff and what to submit (repo, demo link, video?)
Is "Best Open-Source AI Project" listed on the Yaoundé challenge page?
Which category to select on the form
Final name: "ScamSignal CM" is the working name (it lives in APP_NAME). Quick check that no existing product uses it.
Pidgin warning phrases and ask verbs in rules.json (native speaker)
License of the exact Qwen2.5 size we use (0.5B)
Official sender IDs used by MTN MoMo and Orange Money for real transaction SMS (C)
Official customer-service contacts and USSD codes before putting any in advice templates (C)
Hosting RAM, if a public link is needed (A)
Web Share Target works on the demo phone, only if doing the stretch (B)
Cameroon personal data law reference, before citing it in README

17. Success criteria (definition of done)

Public repo with an OSI license and a complete README
Demo returns label, reasons, why and advice for EN, FR and Pidgin examples
Decision-table unit tests pass (including "model can't lower a label")
PIN-warning unit test passes (legit warnings not flagged; warning + ask still flagged)
Privacy canary test passes
python eval/eval.py reproduces the README numbers (Tables A and B, n stated)
One documented failure
Submission completed before the cutoff

18. Roadmap (after Hack Day, for the pitch slide)

Goal: meet users where they already are, without blocking and without surprise data access.

Share instead of paste: installable PWA with "Share → ScamSignal CM" on Android, then a native Android app with share target and "Check with ScamSignal CM" in the text-selection menu (no restricted permissions needed).
WhatsApp bot via the official WhatsApp Cloud API: forward a message, get a reply. Task-specific, so it should fit Meta's 2026 rules for AI on WhatsApp (to be confirmed). Never unofficial WhatsApp libraries.
Opt-in on-device warning label (Android): reads notifications from the SMS app and WhatsApp only, runs rules only on the phone, posts a separate warning notification, never hides or blocks the original, stores nothing. F-Droid first. Hard parts: Android restricts these permissions for sideloaded apps, Google Play strictly limits SMS access, phone makers kill background apps, and we must not train users into the same "allow restricted settings" habit that banking malware exploits.
Feature phones: forward a suspicious SMS to a ScamSignal CM number and get an SMS reply. Needs an operator or aggregator partner.
Data: consented, de-identified French and Pidgin examples from the community; then fine-tune a small multilingual classifier on openly licensed data.

Not planned: USSD message checking (you can't paste a message into USSD), iOS SMS filtering (low reach, junk-folder only), automatic blocking.



Later list: new ideas during the build go in the README "Later" section with the author's name. They are not built today.
