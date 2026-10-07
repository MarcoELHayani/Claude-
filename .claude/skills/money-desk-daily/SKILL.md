---
name: money-desk-daily
description: The weekday Money Desk run. Bob files new receipts, Bill updates invoices and sends due chasers, Axel picks up new subscriptions, cancel confirmations and retention offers. Ends with a short note to Marco only if something needs him. Triggered by the weekday routine or "run the money desk".
---

# Money Desk — daily run

Order matters: Bob first (receipts feed Axel), Bill second (time-sensitive), Axel last.

0. Fetch the Notion Money Desk page (id given in the routine prompt), copy its `Money Desk config` JSON block to `config/money-desk.json`. Then `cd` to the repo, `python3 -m unittest discover -s tests -t . -q`. If tests fail, stop and email Marco the failure; never chase on broken rules.
1. **Bob** — `.claude/skills/bob` steps 1–2 (daily window).
2. **Bill** — `.claude/skills/bill` sections B then C.
3. **Axel** — `.claude/skills/axel` steps 1–2 on the daily window, 4 (only rows already `Cancel approved`), 5.
4. **Early exit:** if Bob filed nothing, Bill had no decisions and Axel found nothing new, stop here. No email.
5. **Only when something needs Marco** (hold, flag_call, fix, Unknown entity, cancel waiting for a click, retention offer, anomaly): send ONE email to `owner.email`, subject `Money Desk: <n> things need you`, plain text, max 10 bullets, each with the link. Chasers Bill sent go in as one line each so Marco knows what went out.

Never re-send a chaser in the same day: `Last chased == today` means already done.
