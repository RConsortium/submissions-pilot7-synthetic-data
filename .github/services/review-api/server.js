/** GitHub App user authorization and fixed-destination review submission. */
import { createServer } from 'node:http';
import { randomBytes, createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { reviewComment } from '../../../docs/assets/dashboard/review-comment.js';

const dashboard = JSON.parse(readFileSync(new URL('../../dashboard.json', import.meta.url)));
const studies = JSON.parse(readFileSync(new URL('../../yamaa-studies.json', import.meta.url)));
const comments = dashboard.comments;
const random = () => randomBytes(32).toString('hex');
const fail = (status, message) => Object.assign(new Error(message), { status });
const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...headers },
});
function publicUrl(value) {
  const url = new URL(value);
  if ((url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname))) || url.username || url.password || url.search || url.hash)
    throw Error('Configure an HTTPS public URL (HTTP is allowed only on localhost).');
  return url;
}

export function createReviewApi(env, { fetch: request = fetch, now = Date.now } = {}) {
  const site = publicUrl(env.SITE_URL), service = publicUrl(env.SERVICE_URL);
  if (service.pathname !== '/' || !env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET)
    throw Error('SERVICE_URL must be an origin; GitHub App client ID and secret are required.');
  const callback = `${service.origin}/auth/callback`;
  const states = new Map(), sessions = new Map(), locks = new Map();
  function prune(map) {
    for (const [key, value] of map) if (value.expires <= now()) map.delete(key);
  }
  async function upstream(url, options) {
    let response;
    try { response = await request(url, { ...options, redirect: 'error', signal: AbortSignal.timeout(20000) }); }
    catch { throw fail(502, 'GitHub could not be reached. Your draft is retained. Check the discussion before retrying.'); }
    if (!response.ok) throw fail(response.status === 401 ? 401 : 502, 'GitHub rejected the request. Your draft is retained.');
    return response.json();
  }
  async function graphql(token, query, variables) {
    const data = await upstream('https://api.github.com/graphql', {
      method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'User-Agent': 'pilot7-review' },
      body: JSON.stringify({ query, variables }),
    });
    if (data.errors?.length || !data.data) throw fail(502, 'GitHub could not complete the review. Check the discussion before retrying.');
    return data.data;
  }
  async function body(req) {
    if (req.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') throw fail(415, 'Expected JSON.');
    const text = await req.text();
    if (Buffer.byteLength(text) > 24000) throw fail(413, 'Review is too large.');
    try { const value = JSON.parse(text); if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error(); return value; } catch { throw fail(400, 'Invalid JSON.'); }
  }
  function session(req) {
    const key = req.headers.get('authorization')?.replace(/^Bearer /, '');
    const value = sessions.get(key);
    if (!value) throw fail(401, 'Sign in with GitHub to submit your review.');
    return value;
  }
  function assessment(input) {
    const { model, issue, review, requestId } = input;
    if (!model || !Object.hasOwn(studies, model.id) || !/^[a-f0-9]{40}$/.test(model.revision || '') ||
        !issue || !/^[A-Z][A-Z0-9]{0,31}$/.test(issue.dataset || '') ||
        typeof issue.id !== 'string' || !issue.id.startsWith(`${model.id}:`) || issue.id.length > 300 ||
        typeof issue.title !== 'string' || issue.title.length > 1000 ||
        (issue.variable && !/^[A-Z][A-Z0-9_]{0,63}$/.test(issue.variable)) ||
        !Array.isArray(issue.check_ids) || issue.check_ids.length > 200 || issue.check_ids.some(id => typeof id !== 'string' || id.length > 300) ||
        !review || typeof review.comment !== 'string' || review.comment.length > 10000 ||
        !/^[a-f0-9-]{36}$/.test(requestId || '')) throw fail(400, 'Invalid review context.');
    const page = new URL(`studies/${model.id}/`, site.href.endsWith('/') ? site : `${site.href}/`);
    let text;
    try { text = reviewComment(model, issue, review, page.href); }
    catch { throw fail(400, 'Choose both agreement and criticality before submitting.'); }
    return { text: `${text}\n\n<!-- pilot7-review:${requestId} -->`, term: comments.term_prefix + model.id + '/' + issue.dataset };
  }
  async function discussion(token, term) {
    const [owner, name] = comments.repo.split('/');
    let after = null;
    do {
      const data = await graphql(token, `query($owner:String!,$name:String!,$after:String){repository(owner:$owner,name:$name){discussions(first:100,after:$after){nodes{id title category{id}} pageInfo{hasNextPage endCursor}}}}`, { owner, name, after });
      const page = data.repository?.discussions;
      if (!page) throw fail(502, 'The review discussion repository is unavailable.');
      const found = page.nodes.find(d => d.title === term && d.category.id === comments.category_id);
      if (found) return found.id;
      after = page.pageInfo.hasNextPage ? page.pageInfo.endCursor : null;
    } while (after);
    const created = await graphql(token, `mutation($repositoryId:ID!,$categoryId:ID!,$title:String!,$body:String!){createDiscussion(input:{repositoryId:$repositoryId,categoryId:$categoryId,title:$title,body:$body}){discussion{id}}}`, {
      repositoryId: comments.repo_id, categoryId: comments.category_id, title: term,
      body: `# ${term}\n\nReviews from the Pilot 7 dashboard.\n\n${site.href}`,
    });
    if (!created.createDiscussion?.discussion?.id) throw fail(502, 'GitHub did not return a discussion.');
    return created.createDiscussion.discussion.id;
  }
  async function post(user, review) {
    const id = await discussion(user.token, review.term);
    // Recover a completed write when an earlier response was lost. Never post twice.
    let after = null;
    do {
      const data = await graphql(user.token, `query($id:ID!,$after:String){node(id:$id){... on Discussion{comments(first:100,after:$after){nodes{body url author{login}} pageInfo{hasNextPage endCursor}}}}}`, { id, after });
      const page = data.node?.comments;
      if (!page) throw fail(502, 'GitHub comments could not be checked before submission.');
      const found = page.nodes.find(c => c.body === review.text && c.author?.login === user.login);
      if (found) return { url: found.url, login: user.login };
      after = page.pageInfo.hasNextPage ? page.pageInfo.endCursor : null;
    } while (after);
    const result = await graphql(user.token, `mutation($discussionId:ID!,$body:String!){addDiscussionComment(input:{discussionId:$discussionId,body:$body}){comment{url}}}`, { discussionId: id, body: review.text });
    const url = result.addDiscussionComment?.comment?.url;
    if (!url?.startsWith(`https://github.com/${comments.repo}/discussions/`)) throw fail(502, 'GitHub did not confirm a comment. Check the discussion before retrying.');
    return { url, login: user.login };
  }
  function authPage(state, result) {
    const nonce = random(), data = JSON.stringify({ type: 'pilot7-github-auth', nonce: state.nonce, ...result }).replaceAll('<', '\\u003c');
    return new Response(`<!doctype html><title>GitHub sign-in</title><p>Return to the review page. You can close this window.</p><script nonce="${nonce}">if(window.opener){window.opener.postMessage(${data},${JSON.stringify(site.origin)});window.close();}</script>`, {
      headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': `default-src 'none'; script-src 'nonce-${nonce}'; frame-ancestors 'none'; base-uri 'none'` },
    });
  }
  async function route(req) {
    prune(states); prune(sessions);
    const url = new URL(req.url);
    if (url.pathname === '/health' && req.method === 'GET') return json({ ok: true });
    if (url.pathname === '/auth/callback' && req.method === 'GET') {
      const state = states.get(url.searchParams.get('state'));
      states.delete(url.searchParams.get('state'));
      if (!state) throw fail(400, 'GitHub sign-in expired. Close this window and try again.');
      try {
        if (!url.searchParams.get('code') || url.searchParams.has('error')) throw fail(400, 'GitHub sign-in was cancelled. Your draft is retained.');
        const result = await upstream('https://github.com/login/oauth/access_token', {
          method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
          body: JSON.stringify({ client_id: env.GITHUB_CLIENT_ID, client_secret: env.GITHUB_CLIENT_SECRET, code: url.searchParams.get('code'), redirect_uri: callback }),
        });
        if (!result.access_token) throw fail(401, 'GitHub sign-in was not completed.');
        const user = await upstream('https://api.github.com/user', { headers: { Authorization: `Bearer ${result.access_token}`, 'User-Agent': 'pilot7-review' } });
        if (!/^[a-z0-9-]+$/i.test(user.login || '')) throw fail(502, 'GitHub did not identify the reviewer.');
        const key = random();
        if (sessions.size >= 1000) throw fail(503, 'Sign-in is busy. Try again later.');
        sessions.set(key, { token: result.access_token, login: user.login, expires: now() + Math.min(Number(result.expires_in) || 3600, 3600) * 1000, submissions: new Map() });
        return authPage(state, { session: key, login: user.login });
      } catch (error) { return authPage(state, { error: error.status ? error.message : 'GitHub sign-in could not be completed. Try again.' }); }
    }
    if (req.headers.get('origin') !== site.origin) throw fail(403, 'This origin is not allowed.');
    if (req.method === 'OPTIONS') return new Response(null, { status: 204 });
    if (req.method !== 'POST') throw fail(405, 'Method not allowed.');
    if (url.pathname === '/auth/start') {
      const input = await body(req);
      if (!/^[a-f0-9-]{36}$/.test(input.nonce || '')) throw fail(400, 'Invalid sign-in request.');
      if (states.size >= 1000) throw fail(429, 'Too many pending sign-ins. Try again later.');
      const key = random(); states.set(key, { nonce: input.nonce, expires: now() + 300000 });
      const authorize = new URL('https://github.com/login/oauth/authorize');
      for (const [k, v] of Object.entries({ client_id: env.GITHUB_CLIENT_ID, redirect_uri: callback, state: key })) authorize.searchParams.set(k, v);
      return json({ url: authorize.href });
    }
    const user = session(req);
    if (url.pathname === '/logout') {
      sessions.delete(req.headers.get('authorization').slice(7)); return json({ ok: true });
    }
    if (url.pathname !== '/reviews') throw fail(404, 'Not found.');
    const input = await body(req), review = assessment(input);
    const hash = createHash('sha256').update(review.text).digest('hex');
    const prior = user.submissions.get(input.requestId);
    if (prior) {
      if (prior.hash !== hash) throw fail(409, 'This submission changed. Start a new submission.');
      return json(await prior.promise);
    }
    if (user.submissions.size >= 100) throw fail(429, 'Review limit reached. Sign in again to continue.');
    // Serialize per thread, including retries, to prevent duplicate thread creation.
    const previous = locks.get(review.term) || Promise.resolve();
    const promise = previous.catch(() => {}).then(() => post(user, review));
    locks.set(review.term, promise);
    user.submissions.set(input.requestId, { hash, promise });
    try { return json(await promise); }
    catch (error) { user.submissions.delete(input.requestId); throw error; }
    finally { if (locks.get(review.term) === promise) locks.delete(review.term); }
  }
  return async req => {
    let response;
    try { response = await route(req); }
    catch (error) { response = json({ error: error.status ? error.message : 'Review service unavailable. Your draft is retained.' }, error.status || 500); }
    if (req.headers.get('origin') === site.origin) {
      response.headers.set('Access-Control-Allow-Origin', site.origin);
      response.headers.set('Vary', 'Origin');
      response.headers.set('Access-Control-Allow-Methods', 'POST, OPTIONS');
      response.headers.set('Access-Control-Allow-Headers', 'Authorization, Content-Type');
    }
    response.headers.set('X-Content-Type-Options', 'nosniff');
    return response;
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const handle = createReviewApi(process.env);
  createServer(async (incoming, outgoing) => {
    try {
      const chunks = []; let size = 0;
      for await (const chunk of incoming) {
        size += chunk.length;
        if (size > 24000) { outgoing.writeHead(413); outgoing.end('Review is too large.'); return; }
        chunks.push(chunk);
      }
      const response = await handle(new Request(new URL(incoming.url, process.env.SERVICE_URL), {
        method: incoming.method, headers: incoming.headers,
        ...(['GET', 'HEAD'].includes(incoming.method) ? {} : { body: Buffer.concat(chunks) }),
      }));
      outgoing.writeHead(response.status, Object.fromEntries(response.headers));
      outgoing.end(Buffer.from(await response.arrayBuffer()));
    } catch { outgoing.writeHead(500); outgoing.end('Review service unavailable.'); }
  }).listen(Number(process.env.PORT || 8080), '0.0.0.0');
}
