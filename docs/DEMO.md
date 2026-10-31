# Demo script (2:00)

Run before going on stage:

```bash
set -a; source .env; set +a
.venv/bin/uvicorn app.main:app --port 8000   # open http://localhost:8000
curl -s localhost:8000/health                 # expect "model_loaded": true
```

If the venue Wi-Fi fails, start without loading `.env`: the app runs rules-only and every label below still holds
(the "Why AI" step then shows *No warning signs found*, and we say so).

| Time | Step | What to click / say | Expected |
|---|---|---|---|
| 0:00 | Hook (15 s) | A real story from the team or the room: who has received a "you won" or "wrong transfer" message? | |
| 0:15 | English (20 s) | **EN scam** (reward + PIN, from a phone number) | **Suspicious**: asks for your PIN, promises a prize. Read the why and the safe next step. |
| 0:35 | French (15 s) | **FR scam** ("renvoyez-les", wrong transfer) | **Suspicious**: asks you to send back money sent "by mistake". Reasons and advice in French. |
| 0:50 | Pidgin (15 s) | **Pidgin scam** | **Suspicious**. Say honestly: Pidgin is experimental and its text still needs a native-speaker review. |
| 1:05 | Legitimate (10 s) | **Real message** (named sender, contains "Never share your PIN") | **No warning signs found**. Point out: we never say "safe", and the PIN warning did not trigger it. |
| 1:15 | Honest failure (15 s) | Paste the failure message below, sender **Named sender** | **Suspicious**, which is wrong. Explain why (below). |
| 1:30 | Why AI (15 s) | **Tricky scam** (fake "uncle on a new line", no scam keywords) | Rules alone: no warning signs. With Gemma: **Unclear**, with an explanation of the impersonation. The model can only raise a clean message to unclear; it can never lower a rule label or say "suspicious" alone. |
| 1:45 | Close (15 s) | Roadmap: share-to-app on Android, WhatsApp bot, on-device local model. Open source: "add rules for your language in rules/rules.json". | |

## Honest failure

Message (synthetic):

> MTN MoMo: You are withdrawing 10,000 FCFA at agent PAUL T. To approve, dial \*126# and enter your PIN.

Result: **Suspicious** (`pin_request`, `agent_impersonation`). Real withdrawal approvals can ask you to enter your PIN
in the official USSD menu, and our PIN rule only looks for "enter … PIN". It cannot tell "type your PIN into the
official menu" from "send your PIN to this person". This is a false alarm on a legitimate flow; fixing it needs a
human-written dev set and verified official message formats (PRD §16).

## Evaluation

Not shown: there is no human-written test set yet, and we chose not to let an AI write it, since the same AI wrote
the rules. `python eval/eval.py` is ready and will print Tables A and B once the files exist.

## Backup

Record a screen capture of this full script before the presentation and keep it on the laptop and a phone.
