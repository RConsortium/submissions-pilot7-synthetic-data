import test from 'node:test';
import assert from 'node:assert/strict';
import { createReviewSubmission } from '../../../docs/assets/dashboard/review-submit.js';
const config = { direct_submission_url: 'https://reviews.example.org', repo: 'elong0527/yamaa' };
const model = { id: 'cdiscpilot01', revision: 'a'.repeat(40) };
const issue = { id: 'cdiscpilot01:ADAE.FLAG.test', dataset: 'ADAE', title: 'Finding', check_ids: [] };
const review = { agreement: 'agree', criticality: 'critical', comment: 'Review' };
function browser() {
  let receive, popup, nonce, closed = false;
  const requests = [];
  const window = {
    crypto: { randomUUID: () => crypto.randomUUID() },
    open: () => popup = { closed, close() { this.closed = true; }, location: {} },
    addEventListener: (_, fn) => { receive = fn; }, removeEventListener: () => { receive = null; },
    setTimeout: () => 1, clearTimeout() {}, setInterval: () => 2, clearInterval() {},
    fetch: async (url, options) => {
      const data = JSON.parse(options.body); requests.push({ url: String(url), options, data });
      if (String(url).endsWith('/auth/start')) { nonce = data.nonce; return Response.json({ url: 'https://github.com/login/oauth/authorize?client_id=app' }); }
      return Response.json({ url: 'https://github.com/elong0527/yamaa/discussions/1#discussioncomment-2', login: 'reviewer' });
    },
  };
  return { window, requests, get nonce() { return nonce; }, message(data = {}, origin = config.direct_submission_url, source = popup) { receive?.({ origin, source, data: { type: 'pilot7-github-auth', nonce, session: 'a'.repeat(64), login: 'reviewer', ...data } }); } };
}
test('unconfigured sites retain the existing workflow and invalid service URLs are rejected', () => {
  assert.equal(createReviewSubmission({}, {}), null);
  for (const url of ['http://evil.example', 'https://user:secret@example.org', 'https://example.org/path']) assert.throws(() => createReviewSubmission({ direct_submission_url: url }, {}));
});
test('sign-in requires matching service origin, popup source and nonce; credentials stay in memory', async () => {
  const b = browser(), client = createReviewSubmission(config, b.window), pending = client.signIn();
  await Promise.resolve(); await Promise.resolve();
  b.message({}, 'https://evil.example'); b.message({}, config.direct_submission_url, {}); b.message({ nonce: 'wrong' });
  assert.equal(client.login, '');
  b.message(); assert.equal(await pending, 'reviewer');
  await client.submit(model, issue, review); await client.submit(model, issue, review);
  const posts = b.requests.filter(r => r.url.endsWith('/reviews'));
  assert.equal(posts.length, 2); assert.equal(posts[0].data.requestId, posts[1].data.requestId);
  assert.equal(posts[0].options.headers.Authorization, `Bearer ${'a'.repeat(64)}`);
  assert.equal(posts[0].options.credentials, 'omit');
  assert.equal(posts[0].data.issue.dataset, 'ADAE');
  await client.signOut(); assert.equal(client.login, '');
  await assert.rejects(client.submit(model, issue, review), /Sign in/);
});
test('blocked popups and expired sessions retain actionable errors without a success URL', async () => {
  const b = browser(); b.window.open = () => null;
  await assert.rejects(createReviewSubmission(config, b.window).signIn(), /Allow.*popup/);
  const c = browser(), client = createReviewSubmission(config, c.window), pending = client.signIn();
  await Promise.resolve(); await Promise.resolve(); c.message(); await pending;
  c.window.fetch = async () => Response.json({ error: 'Sign in again.' }, { status: 401 });
  await assert.rejects(client.submit(model, issue, review), /Sign in again/); assert.equal(client.login, '');
});
