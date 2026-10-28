// Run with a local Firestore emulator and @firebase/rules-unit-testing installed.
// This test only uses demo-ratchetport; it cannot access the production project.
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {createMockUserToken} = require('@firebase/util');
const {initializeTestEnvironment, assertSucceeds, assertFails} = require('@firebase/rules-unit-testing');
const {doc, setDoc, getDoc, getDocs, collection, updateDoc, deleteDoc, serverTimestamp} = require('firebase/firestore');
(async () => {
  const env = await initializeTestEnvironment({projectId: 'demo-ratchetport', firestore: {
    rules: fs.readFileSync(path.join(__dirname, '../services/diagnostics/firestore.rules'), 'utf8'),
    host: '127.0.0.1', port: 8087,
  }});
  try {
    const db = env.authenticatedContext('alice', {firebase: {sign_in_provider: 'anonymous'}}).firestore();
    const guest = env.unauthenticatedContext().firestore();
    const other = env.authenticatedContext('bob', {firebase: {sign_in_provider: 'anonymous'}}).firestore();
    const id = '12345678-1234-1234-1234-123456789012';
    const data = {schema: 1, id, uid: 'alice', version: '1.7', created_utc: '2026-10-28T00:00:00Z',
      exit_code: 0, log: 'Hardware: test\nGPU test', received_at: serverTimestamp()};
    const report = doc(db, 'diagnostics/alice_'+id);
    await env.clearFirestore();
    await assertFails(setDoc(doc(guest, report.path), data));
    await assertFails(setDoc(doc(other, report.path), data));
    for (const bad of [{schema: true}, {schema: 2}, {uid: 'bob'}, {extra: 'field'},
      {log: 'x'.repeat(32769)}, {log: 'ش'.repeat(16385)}, {exit_code: '0'},
      {received_at: new Date('2020-01-01')}, {version: 'wrong'}, {id: '../wrong'}]) {
      await assertFails(setDoc(report, {...data, ...bad}));
    }
    await assertSucceeds(setDoc(report, {...data, log: 'ش'.repeat(16384)}));
    await assertFails(getDoc(report));
    await assertFails(getDocs(collection(db, 'diagnostics')));
    await assertFails(getDoc(doc(other, report.path)));
    await assertFails(updateDoc(report, {log: 'changed'}));
    await assertFails(setDoc(report, data));
    await assertFails(deleteDoc(report));
    await assertFails(setDoc(doc(db, 'another/test'), data));
    await env.withSecurityRulesDisabled(async context => {
      const snapshot = await getDoc(doc(context.firestore(), report.path));
      if (!snapshot.exists()) throw Error('Report was not stored');
    });
    // Exercise the production Python encoder and POST transport against the emulator.
    const jwt = createMockUserToken({sub: 'alice', firebase: {sign_in_provider: 'anonymous'}}, 'demo-ratchetport');
    const script = `import sys, json
sys.path.insert(0, 'scripts')
import session_diagnostics as d
payload = {'schema': 1, 'id': '22222222-1234-1234-1234-123456789012', 'version': '1.7', 'created_utc': '2026-10-28T00:00:00Z', 'exit_code': 3, 'log': 'GPU local emulator test'}
reply = d.request_json('http://127.0.0.1:8087/v1/projects/demo-ratchetport/databases/(default)/documents:commit', d.firestore_write(payload, {'project_id': 'demo-ratchetport'}, 'alice'), sys.argv[1])
assert len(reply['writeResults']) == 1 and reply['writeResults'][0]['updateTime'] and reply['commitTime']
print('Python REST commit: PASS')
`;
    process.stdout.write(execFileSync(process.env.PYTHON || 'python', ['-c', script, jwt], {
      cwd: path.join(__dirname, '..'), encoding: 'utf8', timeout: 20000,
    }));
    console.log('Firestore rules: PASS (create, schema, identity, UTF-8 bounds, timestamp, read/update/delete denial)');
  } finally { await env.cleanup(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
