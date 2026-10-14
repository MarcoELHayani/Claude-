---
name: friday-report
description: Friday Money Desk report. Collects what Axel cancelled, what Bill got paid and chased, and what Bob filed this week; writes the weekly page under Notion › Money Desk and prepares an internal summary for Marco. Triggered by the Friday routine or "money desk report".
---

# Friday report

1. Run the daily run first (`.claude/skills/money-desk-daily`) so the numbers are fresh, but skip its step 5 email; this report replaces it.
2. Week = Monday to today (Europe/Vilnius). Query Notion:
   - Subscriptions: `Cancelled on` in week → `cancelled`; Status in (Active, Review, Keep, Cancel approved, Cancel requested) with Cycle ≠ Usage → `subscriptions_active`.
   - Invoices: `Paid on` in week → `paid`; Status in (Sent, Overdue, Blocked) → `outstanding`; `Last chased` in week → `chasers`.
   - Receipts: `Filed` in week → `filed`.
   - Anything open for Marco (holds, call flags, cancels waiting for his click, retention offers, Unknown entities) → `needs_marco` strings.
3. Write `week.json` (format: `tests/test_moneydesk.py::ReportTest`) and run `python3 -m moneydesk report week.json`. Use its numbers verbatim. All five source collections must be present; use an empty list only after a successful read proves it empty. If a source is unavailable, retain unknown status and report that limitation instead of fabricating zero totals.
4. Notion: find the existing report by week and source IDs first; update it rather than create a duplicate. Keep the existing Money Desk location. Every completion needs source link, actor, timestamp and verification. A payment observed is not money collected by a bot; a ledger entry is not a verified archive. Separate vendor receipt evidence from bank settlement. Report cancellation savings as an estimate, not realised cash.
5. Keep the report internal. An emailed copy is a draft only and requires Marco's approval; no automated sending.
6. Bob's Friday check: make sure this month's Drive folder `Receipts/YYYY-MM` exists and has files from this week; if absent, inspect actual run records and eligible attachments before concluding failure. A quiet week is not proof that the script is broken. Record the precise unverified condition once.
