import test from 'node:test';
import assert from 'node:assert/strict';
import { createReviewApi } from './server.js';

const env = { SITE_URL: 'https://rconsortium.github.io/submissions-pilot7-synthetic-data/', SERVICE_URL: 'https://reviews.example.org', GITHUB_CLIENT_ID: 'client', GITHUB_CLIENT_SECRET: 'secret' };
const origin = new URL(env.SITE_URL).origin;
const nonce = '12345678-1234-1234-1234-123456789abc';
const input = () => ({ requestId: nonce, model: { id: 'cdiscpilot01', revision: 'a'.repeat(40) }, issue: { id: 'cdiscpilot01:ADAE.FLAG.test', dataset: 'ADAE', variable: 'FLAG', title: 'Confirm the rule', check_ids: ['check'] }, review: { agreement: 'agree', criticality: 'critical', comment: 'Use the documented rule.' } });
function fixture({ missing = false, paginate = false } = {}) {
  let clock = 1000, writes = 0, creates = 0, loseResponse = false, deny = false;
  const saved = [];
  const calls = [];
  const api = createReviewApi(env, { now: () => clock, fetch: async (url, options) => {
    calls.push({ url, options });
    if (url.includes('/access_token')) return Response.json({ access_token: 'github-user-token', expires_in: 3600 });
    if (url.endsWith('/user')) return Response.json({ login: 'reviewer' });
    assert.equal(options.headers.Authorization, 'Bearer github-user-token');
    const { query, variables } = JSON.parse(options.body);
    if (deny) return Response.json({ errors: [{ message: 'Permission denied' }] });
    if (query.includes('repository(owner:')) return Response.json({ data: { repository: { discussions: { nodes: missing || (paginate && !variables.after) ? [] : [{ id: 'thread', title: 'pilot7/studies/cdiscpilot01/ADAE', category: { id: 'DIC_kwDOTXVQTs4DFe_t' } }], pageInfo: { hasNextPage: paginate && !variables.after, endCursor: 'next' } } } } });
    if (query.includes('createDiscussion')) { creates++; return Response.json({ data: { createDiscussion: { discussion: { id: 'thread' } } } }); }
    if (query.includes('node(id:')) return Response.json({ data: { node: { comments: { nodes: saved, pageInfo: { hasNextPage: false } } } } });
    if (query.includes('addDiscussionComment')) {
      writes++;
      const url = 'https://github.com/elong0527/yamaa/discussions/42#discussioncomment-123';
      saved.push({ body: variables.body, url, author: { login: 'reviewer' } });
      if (loseResponse) { loseResponse = false; throw Error('Connection lost after write'); }
      return Response.json({ data: { addDiscussionComment: { comment: { url } } } });
    }
    throw Error(`Unexpected query ${query}`);
  } });
  const call = (path, data, session = '', customOrigin = origin) => api(new Request(env.SERVICE_URL + path, {
    method: 'POST', headers: { Origin: customOrigin, 'Content-Type': 'application/json', ...(session ? { Authorization: `Bearer ${session}` } : {}) }, body: JSON.stringify(data),
  }));
  async function auth() {
    const start = await (await call('/auth/start', { nonce })).json();
    const url = new URL(start.url);
    assert.equal(url.searchParams.has('scope'), false, 'GitHub App permissions replace broad OAuth scopes');
    const state = url.searchParams.get('state');
    const callback = await api(new Request(`${env.SERVICE_URL}/auth/callback?state=${state}&code=code`));
    assert.equal(callback.status, 200);
    assert.ok(callback.headers.get('content-security-policy').includes("frame-ancestors 'none'"));
    const html = await callback.text();
    assert.ok(!html.includes('github-user-token'));
    return { session: html.match(/"session":"([a-f0-9]+)"/)[1], state };
  }
  return { api, call, auth, calls, get writes() { return writes; }, get creates() { return creates; }, advance: ms => { clock += ms; }, lose: () => { loseResponse = true; }, deny: () => { deny = true; } };
}

test('authorization rejects foreign origins, callback replay and expired state', async () => {
  const f = fixture();
  const denied = await f.call('/auth/start', { nonce }, '', 'https://evil.example');
  assert.equal(denied.status, 403); assert.equal(denied.headers.has('access-control-allow-origin'), false);
  const { state } = await f.auth();
  assert.equal((await f.api(new Request(`${env.SERVICE_URL}/auth/callback?state=${state}&code=again`))).status, 400);
  const start = await (await f.call('/auth/start', { nonce })).json();
  f.advance(300001);
  assert.equal((await f.api(new Request(`${env.SERVICE_URL}/auth/callback?state=${new URL(start.url).searchParams.get('state')}&code=x`))).status, 400);
});
test('reviews require a live reviewer session and valid fixed-destination context', async () => {
  const f = fixture(); assert.equal((await f.call('/reviews', input())).status, 401);
  const { session } = await f.auth();
  for (const change of [x => x.model.id = 'other-repo', x => x.issue.dataset = '../ADAE', x => x.review.agreement = 'unknown', x => x.review.comment = 'x'.repeat(10001)]) {
    const value = input(); change(value); assert.equal((await f.call('/reviews', value, session)).status, 400);
  }
  assert.equal(f.writes, 0);
  f.advance(3600001); assert.equal((await f.call('/reviews', input(), session)).status, 401);
});
test('posting preserves evidence and reviewer identity, deduplicates concurrent clicks and retries', async () => {
  const f = fixture(), { session } = await f.auth();
  const results = await Promise.all([f.call('/reviews', input(), session), f.call('/reviews', input(), session)]);
  for (const r of results) assert.equal(r.status, 200);
  const result = await results[0].json();
  assert.equal(result.login, 'reviewer'); assert.match(result.url, /discussioncomment-123$/);
  assert.equal(f.writes, 1); assert.equal(f.creates, 0);
  const sent = f.calls.map(c => c.options.body || '').find(b => b.includes('addDiscussionComment'));
  for (const text of ['**Agreement:** Agree', '**Criticality:** Critical', 'a'.repeat(40), 'Use the documented rule.', '/submissions-pilot7-synthetic-data/studies/cdiscpilot01/']) assert.ok(JSON.parse(sent).variables.body.includes(text));
  const changed = input(); changed.review.comment = 'changed';
  assert.equal((await f.call('/reviews', changed, session)).status, 409);
});
test('a lost response is recovered from the exact authored comment before retrying a write', async () => {
  const f = fixture(), { session } = await f.auth(); f.lose();
  assert.equal((await f.call('/reviews', input(), session)).status, 502);
  assert.equal((await f.call('/reviews', input(), session)).status, 200);
  assert.equal(f.writes, 1);
});
test('upstream failure never reports a successful post; sign out invalidates the session', async () => {
  const f = fixture(), { session } = await f.auth(); f.deny();
  const response = await f.call('/reviews', input(), session);
  assert.equal(response.status, 502); assert.equal((await response.json()).url, undefined);
  assert.equal(f.writes, 0);
  assert.equal((await f.call('/logout', {}, session)).status, 200);
  assert.equal((await f.call('/reviews', input(), session)).status, 401);
});

test('missing threads use only the configured repository/category; lookup follows pagination', async () => {
  for (const missing of [true, false]) {
    const f = fixture({ missing, paginate: !missing }), { session } = await f.auth();
    assert.equal((await f.call('/reviews', input(), session)).status, 200);
    assert.equal(f.creates, Number(missing));
    if (missing) {
      const sent = f.calls.map(c => c.options.body || '').find(b => b.includes('createDiscussion'));
      const variables = JSON.parse(sent).variables;
      assert.equal(variables.repositoryId, 'R_kgDOTXVQTg');
      assert.equal(variables.categoryId, 'DIC_kwDOTXVQTs4DFe_t');
      assert.equal(variables.title, 'pilot7/studies/cdiscpilot01/ADAE');
    }
  }
});
test('cancelled authorization reports an error to the bound popup without a session', async () => {
  const f = fixture(), start = await (await f.call('/auth/start', { nonce })).json();
  const state = new URL(start.url).searchParams.get('state');
  const response = await f.api(new Request(`${env.SERVICE_URL}/auth/callback?state=${state}&error=access_denied`));
  const html = await response.text();
  assert.ok(html.includes('GitHub sign-in was cancelled'));
  assert.ok(html.includes(nonce)); assert.ok(!html.includes('"session":'));
  assert.equal(f.calls.length, 0);
});
