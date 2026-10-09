# Bob's receipt saver (Apps Script)

Updated 9 October 2026. This is tested source code, **not an installed service**. Do not put private Notion configuration or receipts in this public repository.

## What it fixes

- Receives PDFs labelled `application/octet-stream`, provided their filename and PDF header identify them. Header detection is a file-type check, not malware scanning.
- Keeps separate attachments when a vendor reuses a filename on the same day.
- Visits new messages in previously processed threads.
- Writes `receipt-index.json` beside monthly PDFs, with source message, attachment name, saved-file URL and digest. This is a document finder, not a paid/unpaid decision engine.
- Uses a script lock and deterministic filenames to recover after a partial write without recreating the same PDF.
- Preserves unrelated scheduled jobs when installing its hourly trigger.

## Validate and activate

1. From this folder run `node --test test-receipt-saver.cjs`. Ten local tests cover replay, MIME mismatch, filename collisions, new messages, partial writes, locking, trigger preservation, old files, backlog scanning and a corrupt index. These use mocked Google services; Google-account integration remains untested.
2. In the existing Apps Script project, preserve the old source and replace only the receipt saver. Use the existing `RECEIPTS_FOLDER_ID` Script Property. `RECEIPTS_TIMEZONE` defaults to the prior script's Europe/Vilnius setting.
3. Run `saveReceipts`. It reads only mail already under `Invoices& Payment/Accountancy`; Bob or the existing authorised connector workflow must identify and label eligible receipts. It does not search every incoming email or infer amounts, entities or payment status.
4. Read back one created PDF and its corresponding index entry. Check message ID, original attachment, digest and Drive link. Re-run and confirm zero new files for those same attachments.
5. Run `install` only after that check. It creates or retains one hourly receipt trigger and preserves unrelated triggers. Record the actual project, trigger, run timestamp and results in the shared task. Do not describe local tests as proof of scheduled execution.
6. Connect Bob to the new existing-ledger fields: `Drive file`, `Archive state`, `Match key`. Upsert by Message ID and also reconcile exact vendor/entity/invoice reference before adding another financial row. A receipt and invoice PDF can represent one transaction. Never mark an invoice paid just because another invoice from the same vendor was paid.

`Has PDF` means an email attachment exists. `Archive state = Drive verified` requires a real saved file and a verified link. The script's PDF label is informational, never the sole deduplication key. Bank reconciliation is separate from vendor payment evidence.

## Limits

One script project must own this job. ScriptLock does not coordinate a second project or another assistant. Duplicate month folders/indexes stop processing for review. The newest 40 threads plus a rotating 40-thread older page are checked per run; this is bounded processing, not an instant full archive. Large mailboxes may need a different cursor strategy. A failed backlog page stays pending. Files are only copied; no existing mail or documents are deleted, sent or shared.

Official interfaces: https://developers.google.com/apps-script/reference/gmail/gmail-attachment and https://developers.google.com/apps-script/reference/script/script-app .
