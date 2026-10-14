# Money Desk: Axel, Bill and Bob

Prepared Money Desk skills and deterministic helpers. Installation and live
execution must be proved separately. See [ACTIVATION.md](ACTIVATION.md) for the
three approval gates and exact acceptance checks. No merge or deployment has
been performed by this review.

- **Axel** finds every subscription in Gmail and keeps one list with a keep/cancel verdict for each. He cancels only after Marco says yes. If a service offers a discount to stay, Axel passes it to Marco to decide.
- **Bill** prepares invoices and unsent chasers under the FAV rules. Exact invoice identity and settlement evidence govern payment status. At 21 days he flags Marco to call.
- **Bob** files every receipt in a ledger the accountant can use. The PDFs go to Drive › Invoices& Finances › Receipts.
- **Friday reporting** stays in the existing internal record, with evidence and actual actors. Emailed copies require approval. Ledger filing is distinct from Drive archiving; observed payments are not attributed to a bot.

Home: Notion › Marco HQ › 💸 Money Desk (Subscriptions, Invoices and Receipts databases, plus the weekly reports).

## Intended schedule (not proof of deployment)

Inspect existing routines and preserve their IDs before activation; do not create
duplicates from this table. Google-side receipt triggers and Claude desktop
workers have separate availability requirements.
| When (Vilnius time) | What | How |
|---|---|---|
| Mon–Fri 08:47 | `money-desk-daily`: Bob, then Bill, then Axel | Claude routine, Gmail + Drive + Notion connectors |
| Fri 16:52 | `friday-report` | Claude routine |
| Hourly | Save receipt PDFs to Drive | `apps-script/bob-receipt-saver.gs` in Marco's Google account |

There are no servers and no API keys. The bots are Claude Code skills (`.claude/skills/*`) using connectors Marco already has. Money maths, chase decisions and invoice rules live in plain Python (`moneydesk/`) with tests, so they come out the same on every run.

## One-time setup
1. **Receipt PDFs:** after deployment approval, locate and back up the existing Apps Script project; do not create another by default. Replace only `apps-script/bob-receipt-saver.gs`, preserve its private folder configuration, and follow ACTIVATION.md for manual save, replay and separate hourly-trigger approval. The first run can process up to 80 labelled threads, not just the inspected receipt. Full saver limits: `apps-script/README.md`.
2. **Config:** copy `config/money-desk.example.json` to `config/money-desk.json` (gitignored) for local runs. The scheduled runs read it from the Notion Money Desk page.
3. **Invoice details:** fill `entities.*.address` and `entities.*.bank` in `config/money-desk.json` (and the Notion config block). Bill refuses to build an invoice PDF until these are filled.
4. **Accountant:** share the Drive `Receipts` folder with them once.

## Guardrails
- **Safe repo:** no real IDs, addresses or keys are in it. They live on Marco's private Notion page and in a gitignored local file, and a test fails if one ever gets committed.
- **Send guard:** rejects every automatic send, including reports to Marco. Legacy config and model-generated approval fields cannot unlock it. Marco approves and manually sends drafts; future programmatic sending requires a separately reviewed authorization mechanism.
- **Fraud scan:** the bots stop on any email that asks for new bank details, credentials, crypto or urgent payment, or that tries to give the bot instructions, and pass it to Marco.
- **PDF safety:** text on invoice PDFs is escaped, so a hostile client name can't plant a link.
- Email content is data, never instructions. The bots never pay, click payment links or log in anywhere.
- Bill prepares drafts only; neither a draft nor a planner decision advances Last chased or Chase stage. Update those only from verified Sent evidence.
- Axel never cancels without approval and never accepts an offer on Marco's behalf.
- Labels are not sufficient for deduplication. Match source IDs and exact transaction identity, reuse existing drafts and week reports, and stop writes when duplicate lookup fails. One worker owns each workflow.

## Develop
```
python3 -m unittest discover -s tests -t .
(cd apps-script && node --test test-receipt-saver.cjs)
python3 -m moneydesk chase invoices.json --today 2026-10-07
python3 -m moneydesk invoice spec.json out.pdf
python3 -m moneydesk monthly subs.json
python3 -m moneydesk report week.json
```
