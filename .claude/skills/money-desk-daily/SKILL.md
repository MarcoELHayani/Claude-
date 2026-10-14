---
name: money-desk-daily
description: The weekday Money Desk run. Bob files new receipts, Bill updates invoices and prepares due chasers, Axel picks up new subscriptions, cancel confirmations and retention offers. Ends with a short note to Marco only if something needs him. Triggered by the weekday routine or "run the money desk".
---

# Money Desk — daily run

Order matters: Bob first (receipts feed Axel), Bill second (time-sensitive), Axel last.

0. Fetch the Notion Money Desk page (id given in the routine prompt), copy its `Money Desk config` JSON block to `config/money-desk.json`. Then `cd` to the repo, `python3 -m unittest discover -s tests -t . -q`. If tests fail, stop and record the failure internally; never chase on broken rules.
1. **Bob** — `.claude/skills/bob` steps 1–2 (daily window).
2. **Bill** — `.claude/skills/bill` sections B then C.
3. **Axel** — `.claude/skills/axel` steps 1–2 on the daily window, 4 (only rows already `Cancel approved`), 5.
4. **Early exit:** if Bob filed nothing, Bill had no decisions and Axel found nothing new, stop here. No email.
5. **Only when something needs Marco** (hold, flag_call, fix, Unknown entity, cancel waiting for a click, retention offer, anomaly): update the existing internal task with at most two essential decisions and source links. Do not email anyone. Lead with actual completed work and actor/output evidence; show drafts separately as Prepared. Do not repeat unchanged blockers. After one retry, stop a failed access path until access changes.

Never re-send a chaser in the same day: `Last chased == today` means already done.
