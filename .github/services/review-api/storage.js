/** Storage contract shared by local tests and the serverless SQLite adapter. */
export class MemoryStore {
  constructor(now = Date.now) { this.now = now; this.records = new Map(); }
  get(kind, key) {
    const value = this.records.get(`${kind}:${key}`);
    return value?.expires > this.now() ? structuredClone(value) : undefined;
  }
  put(kind, key, value) { this.records.set(`${kind}:${key}`, structuredClone(value)); }
  remove(kind, key) { this.records.delete(`${kind}:${key}`); }
  take(kind, key) { const value = this.get(kind, key); this.remove(kind, key); return value; }
  count(kind, prefix = '') {
    return [...this.records].filter(([key, value]) => key.startsWith(`${kind}:${prefix}`) && value.expires > this.now()).length;
  }
  prune() { for (const [key, value] of this.records) if (value.expires <= this.now()) this.records.delete(key); }
}

/** SQLite is owned by one Durable Object; state consumption is transactional. */
export class SqliteStore {
  constructor(storage, now = Date.now) {
    this.storage = storage; this.sql = storage.sql; this.now = now;
    this.sql.exec('CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, key TEXT NOT NULL, expires INTEGER NOT NULL, value TEXT NOT NULL, PRIMARY KEY(kind, key))');
    this.sql.exec('CREATE INDEX IF NOT EXISTS records_expiry ON records(expires)');
  }
  get(kind, key) {
    const rows = this.sql.exec('SELECT value FROM records WHERE kind = ? AND key = ? AND expires > ?', kind, key, this.now()).toArray();
    return rows.length ? JSON.parse(rows[0].value) : undefined;
  }
  put(kind, key, value) {
    this.sql.exec('INSERT OR REPLACE INTO records (kind, key, expires, value) VALUES (?, ?, ?, ?)', kind, key, value.expires, JSON.stringify(value));
  }
  remove(kind, key) { this.sql.exec('DELETE FROM records WHERE kind = ? AND key = ?', kind, key); }
  take(kind, key) {
    return this.storage.transactionSync(() => { const value = this.get(kind, key); this.remove(kind, key); return value; });
  }
  count(kind, prefix = '') {
    return this.sql.exec('SELECT COUNT(*) AS count FROM records WHERE kind = ? AND substr(key, 1, ?) = ? AND expires > ?', kind, prefix.length, prefix, this.now()).one().count;
  }
  prune() { this.sql.exec('DELETE FROM records WHERE expires <= ?', this.now()); }
  async scheduleCleanup() {
    const { expires } = this.sql.exec('SELECT MIN(expires) AS expires FROM records').one();
    if (expires === null) await this.storage.deleteAlarm();
    else await this.storage.setAlarm(Math.max(this.now() + 1000, expires));
  }
}
