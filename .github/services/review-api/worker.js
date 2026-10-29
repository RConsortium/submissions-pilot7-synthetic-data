/** On-demand Worker; one SQLite Durable Object coordinates this review site. */
import { DurableObject } from 'cloudflare:workers';
import { createReviewApi } from './server.js';
import { SqliteStore } from './storage.js';

export class ReviewApi extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.store = new SqliteStore(ctx.storage);
    this.handle = createReviewApi(env, { store: this.store });
    this.tail = Promise.resolve();
  }
  fetch(request) {
    // Keep one request active through external writes. Other events may arrive
    // while fetch awaits GitHub; this queue also protects thread creation.
    const result = this.tail.catch(() => {}).then(async () => {
      try { return await this.handle(request); }
      finally { await this.store.scheduleCleanup(); }
    });
    this.tail = result.then(() => {}, () => {});
    return result;
  }
  alarm() {
    const result = this.tail.catch(() => {}).then(async () => {
      this.store.prune();
      await this.store.scheduleCleanup();
    });
    this.tail = result.then(() => {}, () => {});
    return result;
  }
}

export default {
  fetch(request, env) {
    // idFromName is stable across cold starts and Worker instances.
    return env.REVIEW_API.get(env.REVIEW_API.idFromName('pilot7-review-v1')).fetch(request);
  },
};
