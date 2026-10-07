/**
 * Bob's receipt saver. Runs inside Marco's Google account (script.google.com), free, no AI.
 * Copies every PDF attached to mail under the label "Invoices& Payment/Accountancy"
 * into Drive › Invoices& Finances › Receipts › YYYY-MM, once.
 *
 * Setup (2 minutes):
 *   1. script.google.com → New project → paste this file → Save.
 *   2. Project Settings → Script Properties → add RECEIPTS_FOLDER_ID = the id at the end of
 *      the Receipts folder URL (drive.google.com/drive/folders/<id>). Kept out of the code on purpose.
 *   3. Run `install` once and accept the permissions (Gmail + Drive).
 *   4. Done. It runs every hour. Run `saveReceipts` by hand any time.
 *
 * Safety: it only reads one label, only copies PDFs, never sends, deletes or opens links,
 * and caps file names so a hostile sender name can't do anything odd.
 */
const RECEIPTS_FOLDER_ID = PropertiesService.getScriptProperties().getProperty('RECEIPTS_FOLDER_ID');
const SOURCE_LABEL = 'Invoices& Payment/Accountancy';
const DONE_LABEL = 'Money Desk/PDF saved';
const BATCH = 50;

function install() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('saveReceipts').timeBased().everyHours(1).create();
  saveReceipts();
}

function saveReceipts() {
  // Label objects, not search strings: Gmail search mangles names containing "&" and "/".
  const source = GmailApp.getUserLabelByName(SOURCE_LABEL);
  if (!source) throw new Error('Label not found: ' + SOURCE_LABEL);
  if (!RECEIPTS_FOLDER_ID) throw new Error('Set the RECEIPTS_FOLDER_ID script property first');
  const done = GmailApp.getUserLabelByName(DONE_LABEL) || GmailApp.createLabel(DONE_LABEL);
  const root = DriveApp.getFolderById(RECEIPTS_FOLDER_ID);

  let handled = 0;
  for (let start = 0; handled < BATCH; start += 100) {
    const threads = source.getThreads(start, 100);
    if (!threads.length) break;
    threads
      .filter(th => !th.getLabels().some(l => l.getName() === DONE_LABEL))
      .slice(0, BATCH - handled)
      .forEach(thread => {
        thread.getMessages().forEach(msg => {
          const when = msg.getDate();
          const month = Utilities.formatDate(when, 'Europe/Vilnius', 'yyyy-MM');
          const day = Utilities.formatDate(when, 'Europe/Vilnius', 'yyyy-MM-dd');
          const vendor = clean_(msg.getFrom().replace(/<.*>/, '')) || 'vendor';
          msg.getAttachments({includeInlineImages: false})
            .filter(a => a.getContentType() === 'application/pdf')
            .forEach(a => {
              const folder = subfolder_(root, month);
              const name = `${day} ${vendor} ${clean_(a.getName())}`.slice(0, 150);
              if (!folder.getFilesByName(name).hasNext()) folder.createFile(a.copyBlob().setName(name));
            });
        });
        thread.addLabel(done);
        handled++;
      });
  }
}

function subfolder_(root, name) {
  const it = root.getFoldersByName(name);
  return it.hasNext() ? it.next() : root.createFolder(name);
}

function clean_(s) {
  return String(s).replace(/[^\p{L}\p{N} ._()&-]/gu, '').replace(/\s+/g, ' ').trim().slice(0, 60);
}
