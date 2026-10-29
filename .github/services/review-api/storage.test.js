import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { SqliteStore } from './storage.js';

test('SQLite consumes state once, rejects expired records and schedules physical cleanup', async () => {
  const db = new DatabaseSync(':memory:');
  let now = 1000, alarm = null;
  const storage = {
    sql: { exec(query, ...args) {
      const rows = db.prepare(query).all(...args);
      return { toArray: () => rows, one: () => { assert.equal(rows.length, 1); return rows[0]; } };
    } },
    transactionSync(fn) {
      db.exec('BEGIN');
      try { const result = fn(); db.exec('COMMIT'); return result; }
      catch (error) { db.exec('ROLLBACK'); throw error; }
    },
    async setAlarm(value) { alarm = value; }, async deleteAlarm() { alarm = null; },
  };
  try {
    const store = new SqliteStore(storage, () => now);
    store.put('states', 'nonce', { nonce: 'browser', expires: 2000 });
    store.put('sessions', 'session', { token: 'fake-test-token', expires: 3000 });
    store.put('submissions', 'session:request', { hash: 'hash', result: { url: 'confirmed' }, expires: 3000 });
    assert.equal(store.take('states', 'nonce').nonce, 'browser');
    assert.equal(store.take('states', 'nonce'), undefined);
    assert.equal(store.count('submissions', 'session:'), 1);
    assert.equal(store.count('submissions', 'different-session:'), 0);
    await store.scheduleCleanup(); assert.equal(alarm, 3000);
    now = 3001;
    assert.equal(store.get('sessions', 'session'), undefined);
    assert.equal(store.count('sessions'), 0);
    store.prune();
    assert.equal(db.prepare('SELECT COUNT(*) AS count FROM records').get().count, 0, 'expired tokens and results are physically removed');
    await store.scheduleCleanup(); assert.equal(alarm, null);
  } finally { db.close(); }
});
