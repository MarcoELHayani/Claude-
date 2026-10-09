const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const crypto = require('node:crypto');
const source = fs.readFileSync(__dirname + '/bob-receipt-saver.gs', 'utf8');
function iterator(items) { let n = 0; return {hasNext: () => n < items.length, next: () => items[n++]}; }
function attachment(name, text = '%PDF-1.7\nExample', mime = 'application/octet-stream') {
  return {getName: () => name, getContentType: () => mime, getBytes: () => [...Buffer.from(text)],
    copyBlob() { return {name, text, setName(n) {this.name=n; return this;}, setContentType() {return this;}}; }};
}
function environment() {
  let seq = 0;
  function folder(name) { return {name, files: [], folders: [],
    getFilesByName(n) {return iterator(this.files.filter(f => f.name === n));},
    getFoldersByName(n) {return iterator(this.folders.filter(f => f.name === n));},
    createFolder(n) {const f = folder(n); this.folders.push(f); return f;},
    createFile(blob, content) {
      const f = {id: 'file-' + ++seq, name: typeof blob === 'string' ? blob : blob.name,
        text: typeof blob === 'string' ? content : blob.text,
        getId() {return this.id;}, getName() {return this.name;}, getUrl() {return 'https://drive.test/' + this.id;},
        setContent(s) {if (env.failIndex && this.name === 'receipt-index.json') throw new Error('index unavailable'); this.text=s;},
        getBlob() {return {getDataAsString: () => this.text, getBytes: () => [...Buffer.from(this.text)]};}};
      if (env.failIndex && f.name === 'receipt-index.json') throw new Error('index unavailable');
      this.files.push(f); return f;
    }}; }
  const env = {props: {RECEIPTS_FOLDER_ID: 'test-root'}, threads: [], locked: false, failIndex: false, triggers: [], deleted: [], calls: []};
  env.root = folder('root');
  env.message = (id, atts) => ({getId: () => id, getFrom: () => 'Example Vendor <billing@example.test>',
    getDate: () => new Date('2026-10-08T12:00:00Z'), getSubject: () => 'Invoice', getAttachments: () => atts});
  env.thread = (id, messages) => { const t = {id, messages, labels: [], getId() {return this.id;},
    getMessages() {return this.messages;}, getPermalink() {return 'https://mail.test/' + this.id;}, addLabel(l) {this.labels.push(l);}};
    env.threads.push(t); return t; };
  const context = {console: {log() {}}, Date,
    PropertiesService: {getScriptProperties: () => ({getProperty: k => env.props[k], setProperty: (k,v) => {env.props[k]=v;}})},
    LockService: {getScriptLock: () => ({tryLock() {if (env.locked) return false; env.locked=true; return true;}, releaseLock() {env.locked=false;}})},
    DriveApp: {getFolderById: () => env.root},
    GmailApp: {getUserLabelByName: name => name.includes('Accountancy') ? {getThreads(start,count) {env.calls.push(start); return env.threads.slice(start,start+count);}} : {name}, createLabel: name => ({name})},
    Utilities: {DigestAlgorithm: {SHA_256: 'sha256'}, computeDigest: (_,bytes) => [...crypto.createHash('sha256').update(Buffer.from(bytes)).digest()],
      formatDate: (date,_,format) => date.toISOString().slice(0, format === 'yyyy-MM' ? 7 : 10)},
    ScriptApp: {getProjectTriggers: () => env.triggers, deleteTrigger: t => env.deleted.push(t),
      newTrigger: handler => ({timeBased() {return this;}, everyHours() {return this;}, create() {const t={getHandlerFunction: () => handler}; env.triggers.push(t); return t;}})}
  };
  vm.createContext(context); vm.runInContext(source, context);
  env.run = () => context.saveReceipts(); env.install = () => context.install();
  env.pdfs = () => env.root.folders.flatMap(f => f.files.filter(x => x.name.endsWith('.pdf')));
  env.index = () => JSON.parse(env.root.folders[0].files.find(f => f.name === 'receipt-index.json').text);
  return env;
}

test('generic MIME PDFs are archived with both source locations; replay is idempotent', () => {
  const e=environment(); e.thread('t1',[e.message('m1',[attachment('invoice.pdf')])]);
  assert.equal(e.run().created,1); assert.equal(e.run().created,0); assert.equal(e.pdfs().length,1);
  const docs=Object.values(e.index().documents); assert.equal(docs.length,1);
  assert.equal(docs[0].messageId,'m1'); assert.match(docs[0].driveUrl,/drive.test/); assert.match(docs[0].gmailUrl,/mail.test/);
});
test('same vendor, day and filename with different content are not collapsed', () => {
  const e=environment(); e.thread('t1',[e.message('m1',[attachment('invoice.pdf','%PDF-A')]),e.message('m2',[attachment('invoice.pdf','%PDF-B')])]);
  assert.equal(e.run().created,2); assert.equal(new Set(e.pdfs().map(f=>f.name)).size,2);
});
test('a later message in an already labelled thread is saved', () => {
  const e=environment(); const t=e.thread('t1',[e.message('m1',[attachment('invoice.pdf')])]); e.run();
  t.messages.push(e.message('m2',[attachment('receipt.pdf','%PDF-Receipt')]));
  assert.equal(e.run().created,1); assert.equal(e.pdfs().length,2);
});
test('failed index write retries without creating another PDF', () => {
  const e=environment(); const t=e.thread('t1',[e.message('m1',[attachment('invoice.pdf')])]); e.failIndex=true;
  assert.equal(e.run().errors.length,1); assert.equal(t.labels.length,0); assert.equal(e.props.RECEIPTS_LAST_SUCCESS,undefined);
  e.failIndex=false; assert.equal(e.run().created,0); assert.equal(e.pdfs().length,1); assert.equal(Object.keys(e.index().documents).length,1);
});
test('a renamed executable is not accepted merely because it says pdf', () => {
  const e=environment(); e.thread('t1',[e.message('m1',[attachment('invoice.pdf','MZ-executable')])]);
  assert.equal(e.run().errors.length,1); assert.equal(e.pdfs().length,0); assert.equal(e.locked,false);
});
test('lock prevents concurrent writes', () => {
  const e=environment(); e.locked=true; assert.match(e.run().skipped,/lock/); assert.equal(e.root.folders.length,0);
});
test('installation preserves unrelated triggers and removes only redundant saver triggers', () => {
  const e=environment(); const other={getHandlerFunction:()=> 'otherJob'}, one={getHandlerFunction:()=> 'saveReceipts'}, two={getHandlerFunction:()=> 'saveReceipts'};
  e.triggers=[other,one,two]; e.install(); assert.deepEqual(e.deleted,[two]);
});
test('legacy filename only reuses a file when bytes match', () => {
  const e=environment(); const f=e.root.createFolder('2026-10'); f.createFile(attachment('2026-10-08 Example Vendor invoice.pdf').copyBlob());
  e.thread('t1',[e.message('m1',[attachment('invoice.pdf')])]); assert.equal(e.run().created,0); assert.equal(e.pdfs().length,1);
});
test('older labelled threads are eventually visited through the rotating cursor', () => {
  const e=environment(); for(let i=0;i<95;i++) e.thread('t'+i,[e.message('m'+i,[])]);
  e.run(); assert.equal(e.props.RECEIPTS_CURSOR,'80'); e.run(); assert.equal(e.props.RECEIPTS_CURSOR,'40'); assert.ok(e.calls.includes(80));
});
test('corrupt index is preserved and blocks successful completion', () => {
  const e=environment(); const f=e.root.createFolder('2026-10'); f.createFile('receipt-index.json','not JSON');
  e.thread('t1',[e.message('m1',[attachment('invoice.pdf')])]); assert.equal(e.run().errors.length,1);
  assert.equal(f.files[0].text,'not JSON'); assert.equal(e.pdfs().length,0);
});
