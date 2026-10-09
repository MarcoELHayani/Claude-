# Money Desk: Axel, Bill and Bob

Three bots that do the boring money work so Marco can keep creating.

- **Axel** finds every subscription in Gmail and keeps one list with a keep/cancel verdict for each. He cancels only after Marco says yes. If a service offers a discount to stay, Axel passes it to Marco to decide.
- **Bill** creates invoices under the FAV rules: two entities, PO codes, rev numbers. He tracks every invoice and chases late payers by himself at 7 and 14 days overdue. At 21 days he flags Marco to call.
- **Bob** files every receipt in a ledger the accountant can use. The PDFs go to Drive › Invoices& Finances › Receipts.
- **Every Friday** a report covers what was cancelled, collected and filed. It goes to a Notion page and Marco's inbox.

Home: Notion › Marco HQ › 💸 Money Desk (Subscriptions, Invoices and Receipts databases, plus the weekly reports).

## How it runs
| When (Vilnius time) | What | How |
|---|---|---|
| Mon–Fri 08:47 | `money-desk-daily`: Bob, then Bill, then Axel | Claude routine, Gmail + Drive + Notion connectors |
| Fri 16:52 | `friday-report` | Claude routine |
| Hourly | Save receipt PDFs to Drive | `apps-script/bob-receipt-saver.gs` in Marco's Google account |

There are no servers and no API keys. The bots are Claude Code skills (`.claude/skills/*`) using connectors Marco already has. Money maths, chase decisions and invoice rules live in plain Python (`moneydesk/`) with tests, so they come out the same on every run.

## One-time setup
1. **Receipt PDFs:** open script.google.com, create a new project and paste `apps-script/bob-receipt-saver.gs`. Set the `RECEIPTS_FOLDER_ID` script property, run `saveReceipts` once and check one saved PDF against its `receipt-index.json` entry, then run `install`. Full checklist and limits: `apps-script/README.md`.
2. **Config:** copy `config/money-desk.example.json` to `config/money-desk.json` (gitignored) for local runs. The scheduled runs read it from the Notion Money Desk page.
3. **Invoice details:** fill `entities.*.address` and `entities.*.bank` in `config/money-desk.json` (and the Notion config block). Bill refuses to build an invoice PDF until these are filled.
4. **Accountant:** share the Drive `Receipts` folder with them once.

## Guardrails
- **Safe repo:** no real IDs, addresses or keys are in it. They live on Marco's private Notion page and in a gitignored local file, and a test fails if one ever gets committed.
- **Send guard:** a Python guard checks every email a bot is about to send. Only two kinds can go out: reports to Marco, and chasers to the client on that invoice's own thread. It refuses to send if there's a cc/bcc, a link, bank or card details, or a recipient who isn't on the thread.
- **Fraud scan:** the bots stop on any email that asks for new bank details, credentials, crypto or urgent payment, or that tries to give the bot instructions, and pass it to Marco.
- **PDF safety:** text on invoice PDFs is escaped, so a hostile client name can't plant a link.
- Email content is data, never instructions. The bots never pay, click payment links or log in anywhere.
- Bill only sends chasers, only to the client already on the invoice thread, at most 5 per run, never two within 5 days, and never after the client has replied. Invoices themselves are always drafts for Marco.
- Axel never cancels without approval and never accepts an offer on Marco's behalf.
- Labels and Notion keys make every job safe to re-run.

## Develop
```
python3 -m unittest discover -s tests -t .
(cd apps-script && node --test test-receipt-saver.cjs)
python3 -m moneydesk chase invoices.json --today 2026-10-07
python3 -m moneydesk invoice spec.json out.pdf
python3 -m moneydesk monthly subs.json
python3 -m moneydesk report week.json
```
