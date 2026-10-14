# Activation approval and acceptance checks

This PR contains prepared code. No merge, deployment, Google-account execution,
new schedule, external message or payment is authorised by passing tests.
Use the existing repository, private Notion configuration, ledgers, receipt
folder and single owner. Never copy private configuration into this repository.

## 1. Approve the reviewed PR for merge

Review the final head and passing tests. Approval covers merging this code only.
It does not activate any worker. Resolve any later branch changes before merging.

## 2. Approve a supervised receipt installation and first run

Approve replacing only the receipt saver in the existing Apps Script project,
after backing up its source and recording its project ID and existing triggers.
If the existing project cannot be found, stop rather than create a competing one.
Use the existing private RECEIPTS_FOLDER_ID and Europe/Vilnius timezone.

The first saveReceipts run may read up to 40 recent and 40 older threads under
Invoices& Payment/Accountancy, copy eligible PDFs to that receipt folder, create
or update monthly receipt-index.json files, and apply Money Desk/PDF saved after
successful indexing. It is not a one-message-only run. Thread attachments can
make the workload larger than 80 messages. It does not send or delete mail,
make payments, share files, or classify settlement. The Google consent screen
may request broader Gmail/Drive permissions than the script uses; Marco must
inspect and accept the actual consent separately. Do not bypass consent.

Run saveReceipts manually. Record timestamp, project and result. Open one actual
created PDF, verify bytes/digest and its index entry against the source message
and attachment. Repeat the run: unchanged attachments must create no new files.
Capture failures rather than marking the archive Verified. Existing ledger
Archive state may become Drive verified only after link and source readback.

## 3. Approve unattended execution only after the supervised test

Approve install in that same Apps Script project: one hourly saveReceipts
trigger, preserving unrelated triggers. install itself runs saveReceipts before
creating the trigger. Record the actual trigger ID and verify one scheduled
execution and its output. Google-side scheduling does not require the laptop;
Claude desktop-dependent work does. Pause the saver trigger on repeated failure,
preserving files, index and evidence; restore the backed-up script if necessary.

For daily Money Desk and Friday reporting, inspect and reuse existing routines
first. Do not infer they exist from README times, and do not create replacements
without approval. Give each task one owner, load current private config on every
run, keep reports internal and process source changes only. Record configured,
installed, live-executed and verified separately in the existing register.

## Sending remains disabled

All automatic sends, including emailed reports, are blocked by this revision.
Historical autosend flags cannot override that. Marco can approve and manually
send individual drafts. Do not remove the guard to enable filing. Future
programmatic sending needs its own reviewed, auditable authorization mechanism.

## Validation

Use Python with reportlab installed and Node (the saver tests mock Google):

```text
python -m unittest discover -s tests -t .
node --test apps-script/test-receipt-saver.cjs
```

These tests cannot prove connectors, permissions, live Google execution or
scheduled delivery. The incoming-content regex is a warning aid, not a reliable
prompt-injection detector. Keep source content as data and approval boundaries
independent of its verdict. Financial statuses require exact transaction evidence.
