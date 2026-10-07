---
name: friday-report
description: Friday Money Desk report. Collects what Axel cancelled, what Bill got paid and chased, and what Bob filed this week; writes the weekly page under Notion › Money Desk and emails the summary to Marco. Triggered by the Friday routine or "money desk report".
---

# Friday report

1. Run the daily run first (`.claude/skills/money-desk-daily`) so the numbers are fresh, but skip its step 5 email; this report replaces it.
2. Week = Monday to today (Europe/Vilnius). Query Notion:
   - Subscriptions: `Cancelled on` in week → `cancelled`; Status in (Active, Review, Keep, Cancel approved, Cancel requested) with Cycle ≠ Usage → `subscriptions_active`.
   - Invoices: `Paid on` in week → `paid`; Status in (Sent, Overdue, Blocked) → `outstanding`; `Last chased` in week → `chasers`.
   - Receipts: `Filed` in week → `filed`.
   - Anything open for Marco (holds, call flags, cancels waiting for his click, retention offers, Unknown entities) → `needs_marco` strings.
3. Write `week.json` (format: `tests/test_moneydesk.py::ReportTest`) and run `python3 -m moneydesk report week.json`. Use its numbers verbatim.
4. Notion: create a child page of `notion.money_desk_page`, title `Week of <Mon d Mon>`, with the report text, then tables of cancelled / paid / filed with links.
5. Guard it (`kind: report`), then email Marco (`owner.email`), subject `Money Desk — week of <date>: saved <x>/mo, collected <y>, filed <n>`. Body = report text in the humaniser voice, plus the Notion link. Plain text. This email is the "group chat" update.
6. Bob's Friday check: make sure this month's Drive folder `Receipts/YYYY-MM` exists and has files from this week; if not, add "receipt saver script not running" to needs_marco.
