/** Receipt archive + source index. Replacement for apps-script/bob-receipt-saver.gs.
 * Set RECEIPTS_FOLDER_ID in Script Properties; optionally RECEIPTS_TIMEZONE.
 * Run saveReceipts once and inspect its result before installing its hourly trigger.
 * Only reads the existing Accountancy label. Never sends, deletes, pays or shares.
 * The monthly receipt-index.json is a document locator, NOT a payment ledger.
 */
const SOURCE_LABEL = 'Invoices& Payment/Accountancy';
const DONE_LABEL = 'Money Desk/PDF saved';
const BATCH = 40;
const INDEX_NAME = 'receipt-index.json';

function install() {
  const result = saveReceipts();
  if (result.skipped || !result.complete || result.errors.length) throw new Error('Complete the first run without errors before installing');
  // Preserve every unrelated task in this Apps Script project.
  const ours = ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'saveReceipts');
  if (!ours.length) ScriptApp.newTrigger('saveReceipts').timeBased().everyHours(1).create();
  ours.slice(1).forEach(t => ScriptApp.deleteTrigger(t));
  return result;
}

function saveReceipts() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return {skipped: 'another run owns the lock', errors: []};
  try {
    const props = PropertiesService.getScriptProperties();
    const rootId = props.getProperty('RECEIPTS_FOLDER_ID');
    if (!rootId) throw new Error('Set RECEIPTS_FOLDER_ID first');
    const root = DriveApp.getFolderById(rootId);
    const source = GmailApp.getUserLabelByName(SOURCE_LABEL);
    if (!source) throw new Error('Accountancy source label is missing');
    const timezone = props.getProperty('RECEIPTS_TIMEZONE') || 'Europe/Vilnius';
    const done = GmailApp.getUserLabelByName(DONE_LABEL) || GmailApp.createLabel(DONE_LABEL);
    const cursor = Math.max(BATCH, Number(props.getProperty('RECEIPTS_CURSOR')) || BATCH);
    const recent = source.getThreads(0, BATCH);
    const older = source.getThreads(cursor, BATCH);
    const threads = [...new Map([...recent, ...older].map(t => [t.getId(), t])).values()];
    const result = {threads: 0, attachments: 0, created: 0, reused: 0, errors: [], indexes: []};
    const started = Date.now();
    const months = {};
    let complete = true;
    for (const thread of threads) {
      if (Date.now() - started > 210000) { complete = false; break; }
      try {
        let pdfs = 0;
        // Do NOT skip a labelled thread: a later message can add new attachments.
        for (const msg of thread.getMessages()) {
          const month = Utilities.formatDate(msg.getDate(), timezone, 'yyyy-MM');
          const day = Utilities.formatDate(msg.getDate(), timezone, 'yyyy-MM-dd');
          const vendor = clean_(msg.getFrom().replace(/<.*>/, '')) || 'vendor';
          const attachments = msg.getAttachments({includeInlineImages: false});
          for (let i = 0; i < attachments.length; i++) {
            const a = attachments[i];
            if (!pdfCandidate_(a)) continue;
            const bytes = a.getBytes();
            if (!pdfHeader_(bytes)) throw new Error('PDF candidate has no PDF header: ' + clean_(a.getName()));
            pdfs++;
            const digest = digest_(bytes);
            const key = msg.getId() + ':' + i + ':' + digest;
            const bucket = months[month] || (months[month] = openIndex_(root, month));
            const suffix = '__' + msg.getId() + '_' + i + '_' + digest.slice(0, 12) + '.pdf';
            const stem = day + ' ' + vendor + ' ' + clean_(a.getName().replace(/\.pdf$/i, ''));
            const name = stem.slice(0, 150 - suffix.length) + suffix;
            let file = null;
            // Reconcile an existing indexed file, then deterministic/legacy names.
            const entry = bucket.data.documents[key];
            if (entry) {
              const matches = bucket.folder.getFilesByName(entry.fileName);
              while (matches.hasNext()) { const candidate = matches.next(); if (candidate.getId() === entry.fileId) file = candidate; }
            }
            if (file && digest_(file.getBlob().getBytes()) !== digest) file = null;
            if (!file) file = matchingFile_(bucket.folder, name, digest);
            const legacy = (day + ' ' + vendor + ' ' + clean_(a.getName())).slice(0, 150);
            if (!file) file = matchingFile_(bucket.folder, legacy, digest);
            if (!file) {
              file = bucket.folder.createFile(a.copyBlob().setName(name).setContentType('application/pdf'));
              result.created++;
            } else result.reused++;
            bucket.data.documents[key] = {
              messageId: msg.getId(), attachmentIndex: i, originalName: a.getName(),
              received: msg.getDate().toISOString(), sender: msg.getFrom(), subject: msg.getSubject(),
              sha256: digest, fileId: file.getId(), fileName: file.getName(), driveUrl: file.getUrl(),
              gmailUrl: thread.getPermalink()
            };
            // Persist after each attachment. A retry recovers the same PDF if this write fails.
            bucket.data.updatedAt = new Date().toISOString();
            const json = JSON.stringify(bucket.data, null, 2);
            if (bucket.file) bucket.file.setContent(json);
            else bucket.file = bucket.folder.createFile(INDEX_NAME, json, 'application/json');
            result.attachments++;
          }
        }
        if (pdfs) thread.addLabel(done);
        result.threads++;
      } catch (error) {
        result.errors.push({threadId: thread.getId(), error: String(error.message || error)});
      }
    }
    result.indexes = Object.values(months).filter(b => b.file).map(b => b.file.getUrl());
    if (complete && !result.errors.length) {
      props.setProperty('RECEIPTS_CURSOR', String(older.length === BATCH ? cursor + BATCH : BATCH));
      props.setProperty('RECEIPTS_LAST_SUCCESS', new Date().toISOString());
    }
    result.complete = complete;
    console.log(JSON.stringify(result));
    return result;
  } finally { lock.releaseLock(); }
}

function openIndex_(root, month) {
  const folders = root.getFoldersByName(month);
  const folder = folders.hasNext() ? folders.next() : root.createFolder(month);
  if (folders.hasNext()) throw new Error('Duplicate month folders need reconciliation: ' + month);
  const files = folder.getFilesByName(INDEX_NAME);
  const file = files.hasNext() ? files.next() : null;
  if (files.hasNext()) throw new Error('Duplicate receipt indexes need reconciliation: ' + month);
  const data = file ? JSON.parse(file.getBlob().getDataAsString()) : {version: 1, documents: {}};
  if (data.version !== 1 || !data.documents || typeof data.documents !== 'object' || Array.isArray(data.documents)) {
    throw new Error('Unsupported receipt index; preserve it for review');
  }
  return {folder, file, data};
}

function matchingFile_(folder, name, digest) {
  const files = folder.getFilesByName(name);
  while (files.hasNext()) {
    const file = files.next();
    if (digest_(file.getBlob().getBytes()) === digest) return file;
  }
  return null;
}

function pdfCandidate_(a) {
  return String(a.getContentType() || '').split(';')[0].trim().toLowerCase() === 'application/pdf' || /\.pdf$/i.test(a.getName());
}

function pdfHeader_(bytes) {
  return String.fromCharCode(...bytes.slice(0, 1024).map(b => b & 255)).includes('%PDF-');
}

function digest_(bytes) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, bytes).map(b => (b & 255).toString(16).padStart(2, '0')).join('');
}

function clean_(s) {
  return String(s).replace(/[^\p{L}\p{N} ._()&-]/gu, '').replace(/\s+/g, ' ').trim().slice(0, 60);
}
