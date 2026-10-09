---
name: bob
description: Bob, Marco's receipt filer. Finds every new receipt in Gmail, labels it for the accountant, logs it in Notion (Money Desk › Receipts) with vendor, amount, VAT and entity, and makes sure the PDF lands in Drive › Invoices& Finances › Receipts. Use for "file my receipts", "Bob", or inside the daily Money Desk run.
---

# Bob — receipts

Read `CLAUDE.md` rules first. IDs: `config/money-desk.json`.
Gmail label placeholders like `{filed}` mean `gmail.labels.filed.id` from config; always query by label id.

## 1. Find unfiled receipts
`newer_than:14d -label:{filed} -in:sent (receipt OR invoice OR "order confirmation" OR "payment received" OR ricevuta OR fattura OR "your order") -label:{unpaid} -label:{to_be_deleted}`
plus `label:{accountancy} -label:{filed}`.
Skip: marketing ("% off", newsletters), invoices Marco **issued** (those are Bill's), quotes, shipping-only updates, budget alerts with no charge.
First run only: widen to `newer_than:13m`, max 100 per run, and carry on next run.

## 2. For each receipt
- `python3 -m moneydesk scan` on the body. Flagged → don't file or label it; list it for Marco as "possible fraud: <flags>".
- `get_message` with `PLAIN_TEXT`. Extract vendor, date, total, VAT, currency, receipt/invoice number, and whether there's a PDF attachment (`attachments[].mimeType == application/pdf`).
- Entity: recipient any address in `gmail.entity_by_recipient` → AIV; production gear, editing/AI tools, studio costs → FAV Studios; producer/crew services → Fav Production; clothes, food, personal travel → Personal; unsure → Unknown (list it for Marco, still file it).
- Upsert into Notion Receipts (`notion.receipts_ds`), matched on `Message ID`: Vendor, Date, Amount, VAT, Currency, Entity, Category, Receipt no, Gmail (viewUrl), Message ID, Has PDF.
- Apply Gmail labels `Invoices& Payment/Accountancy` and `Money Desk/Filed` (`label_message`, ids in config). Labelling is what makes it idempotent: always label last, after the Notion write succeeded.

## 3. PDFs into Drive
The Apps Script in `apps-script/bob-receipt-saver.gs` (installed once in Marco's Google account) copies every PDF from the `Invoices& Payment/Accountancy` label into `Receipts/YYYY-MM/` hourly, and writes `receipt-index.json` in each month folder (Message ID, attachment, SHA-256, Drive link). Bob doesn't download attachments (that costs a lot of tokens per receipt).
To link a Drive file, find the row's `Message ID` in that month's index. `Has PDF` only means the email had an attachment; set `Archive state = Drive verified` only when the index entry exists and its Drive link opens. The index is a document finder, never proof of payment.
For receipts with **no** PDF (body-only receipts like many Stripe/Apple mails): Bob creates a Google Doc in `Receipts/YYYY-MM/` (`create_file`, `textContent` = the plain-text receipt, title `YYYY-MM-DD Vendor Amount`) so the accountant has a document for every line.
On Fridays Bob checks the latest month folder exists; if the script hasn't run in 2 days, flag Marco.

## Output (for the daily/Friday run)
Count filed, totals per currency, Unknown-entity items for Marco.
