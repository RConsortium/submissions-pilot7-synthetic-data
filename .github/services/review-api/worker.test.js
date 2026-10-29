import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Miniflare, Log, LogLevel } from 'miniflare';

const origin = 'https://rconsortium.github.io';
const service = 'https://reviews.example.org';
const nonce = '12345678-1234-1234-1234-123456789abc';
const review = { requestId: nonce, model: { id: 'cdiscpilot01', revision: 'a'.repeat(40) }, issue: { id: 'cdiscpilot01:ADAE.FLAG.test', dataset: 'ADAE', variable: 'FLAG', title: 'Confirm the rule', check_ids: ['check'] }, review: { agreement: 'agree', criticality: 'critical', comment: 'Use the documented rule.' } };
const commentUrl = 'https://github.com/elong0527/yamaa/discussions/42#discussioncomment-123';

async function fixture() {
  const directory = await mkdtemp(join(tmpdir(), 'pilot7-worker-'));
  let runtime, writes = 0, lost = false, exchanges = 0;
  const saved = [];
  const github = async request => {
    const url = new URL(request.url);
    if (url.pathname.endsWith('/access_token')) { exchanges++; return Response.json({ access_token: 'github-user-token', expires_in: 3600 }); }
    if (url.pathname === '/user') return Response.json({ login: 'reviewer' });
    assert.equal(request.headers.get('authorization'), 'Bearer github-user-token');
    const { query, variables } = await request.json();
    if (query.includes('repository(owner:')) return Response.json({ data: { repository: { discussions: { nodes: [{ id: 'thread', title: 'pilot7/studies/cdiscpilot01/ADAE', category: { id: 'DIC_kwDOTXVQTs4DFe_t' } }], pageInfo: { hasNextPage: false } } } } });
    if (query.includes('node(id:')) return Response.json({ data: { node: { comments: { nodes: saved, pageInfo: { hasNextPage: false } } } } });
    if (query.includes('addDiscussionComment')) {
      writes++;
      saved.push({ body: variables.body, url: commentUrl, author: { login: 'reviewer' } });
      if (lost) { lost = false; return new Response('Response lost after write', { status: 502 }); }
      return Response.json({ data: { addDiscussionComment: { comment: { url: commentUrl } } } });
    }
    throw Error(`Unexpected GitHub request: ${request.url}`);
  };
  async function restart() {
    if (runtime) await runtime.dispose();
    runtime = new Miniflare({
      modules: true, scriptPath: fileURLToPath(new URL('.build/worker/worker.js', import.meta.url)),
      compatibilityDate: '2026-07-30', log: new Log(LogLevel.ERROR),
      durableObjects: { REVIEW_API: { className: 'ReviewApi', useSQLite: true } },
      durableObjectsPersist: directory,
      bindings: { SITE_URL: origin + '/submissions-pilot7-synthetic-data/', SERVICE_URL: service, GITHUB_CLIENT_ID: 'client', GITHUB_CLIENT_SECRET: 'secret' },
      outboundService: github,
    });
    await runtime.ready;
  }
  await restart();
  const call = (path, body, session = '') => runtime.dispatchFetch(service + path, {
    method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json', ...(session ? { Authorization: `Bearer ${session}` } : {}) }, body: JSON.stringify(body),
  });
  const start = async () => {
    const result = await (await call('/auth/start', { nonce })).json();
    return new URL(result.url).searchParams.get('state');
  };
  const callback = state => runtime.dispatchFetch(`${service}/auth/callback?state=${state}&code=code`);
  async function login(state = null) {
    const response = await callback(state || await start());
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.ok(!html.includes('github-user-token'));
    const session = html.match(/"session":"([a-f0-9]+)"/)?.[1];
    assert.ok(session, html);
    return session;
  }
  return { call, start, callback, login, restart, lose: () => { lost = true; }, get writes() { return writes; }, get exchanges() { return exchanges; }, async close() { await runtime.dispose(); await rm(directory, { recursive: true, force: true }); } };
}

test('real Worker/SQLite survives cold starts: OAuth state, sessions, results and logout', async () => {
  const f = await fixture();
  try {
    const state = await f.start();
    await f.restart();
    const session = await f.login(state);
    assert.equal(f.exchanges, 1);
    await f.restart();
    assert.equal((await f.callback(state)).status, 400, 'one-time state remains consumed after restart');
    const responses = await Promise.all([f.call('/reviews', review, session), f.call('/reviews', review, session)]);
    for (const response of responses) { assert.equal(response.status, 200); assert.equal((await response.json()).url, commentUrl); }
    assert.equal(f.writes, 1);
    await f.restart();
    const replay = await f.call('/reviews', review, session);
    assert.equal(replay.status, 200); assert.equal((await replay.json()).url, commentUrl);
    assert.equal(f.writes, 1, 'completed submission is persisted');
    const changed = structuredClone(review); changed.review.comment = 'Changed';
    assert.equal((await f.call('/reviews', changed, session)).status, 409);
    assert.equal((await f.call('/logout', {}, session)).status, 200);
    await f.restart();
    assert.equal((await f.call('/reviews', review, session)).status, 401);
  } finally { await f.close(); }
});

test('ambiguous writes recover after isolate restart without a duplicate comment', async () => {
  const f = await fixture();
  try {
    const session = await f.login(); f.lose();
    assert.equal((await f.call('/reviews', review, session)).status, 502);
    assert.equal(f.writes, 1);
    await f.restart();
    const result = await f.call('/reviews', review, session);
    assert.equal(result.status, 200); assert.equal((await result.json()).url, commentUrl);
    assert.equal(f.writes, 1);
  } finally { await f.close(); }
});
