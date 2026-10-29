# Serverless GitHub review submission

GitHub Pages hosts the dashboard. Cloudflare Workers handles GitHub App sign-in
and direct submission on demand. A SQLite Durable Object retains OAuth state,
reviewer sessions, and submission results across cold starts. There is no
continuously running server, container, or database process to manage.
Cloudflare usage charges and account limits still apply.

## Deploy and activate

1. Register a GitHub App with **Discussions: Read and write** and the default
   Metadata permission. Enable user authorization. Install it on
   `elong0527/yamaa`, the existing discussion repository in
   `.github/dashboard.json`. The service obtains a user access token, so comments
   appear under the reviewer's identity and GitHub enforces their repository
   access. Do not use an installation/bot token or request broad OAuth App scopes.
2. From `.github/services/review-api/`, install the pinned deployment tools:

   ```bash
   npm ci
   npx wrangler login
   ```

3. Edit `wrangler.jsonc`: choose the Worker `name`, set `SERVICE_URL` to its exact
   HTTPS origin (for example, `https://pilot7-review-api.YOUR-SUBDOMAIN.workers.dev`),
   and replace `GITHUB_CLIENT_ID` with the App's client ID. Keep `SITE_URL` at the
   dashboard's full project URL. Set the App's authorization callback to
   `https://YOUR-WORKER-ORIGIN/auth/callback`.
4. Deploy and set the App secret through Cloudflare's encrypted secret store:

   ```bash
   npm run deploy
   npx wrangler secret put GITHUB_CLIENT_SECRET
   ```

   The secret command prompts for its value; never put it in `wrangler.jsonc`,
   `.github/dashboard.json`, source files, or command arguments. The API is not
   ready until the secret is set. `GET https://YOUR-WORKER-ORIGIN/health` should
   then return `{"ok":true}`. No account ID or credentials are committed here.
   The Wrangler migration creates the SQLite Durable Object automatically;
   no separate database, KV namespace, or manual SQL migration is needed.
5. Set `comments.direct_submission_url` in `.github/dashboard.json` to that
   deployed HTTPS origin and publish the site. It must have no path or query.
   An empty value keeps the copy/paste flow until deployment is ready. Merging
   the PR alone does not deploy a Worker or activate the live feature.
6. Verify with a test reviewer: select both decisions, enter comments, select
   **Submit review to GitHub**, authorize the App in the popup, and follow
   **View GitHub comment**. Confirm the reviewer is the author and the post is
   in the existing dataset thread. Automated tests never post real comments.

Use Node 22.16+ for local tooling. GitHub App secrets and the Worker deployment
require the relevant GitHub/Cloudflare account access. CI only builds and tests;
it does not deploy or receive production secrets.

## State and duplicate protection

The Worker routes every request to the same named Durable Object. It runs only
while handling a request or cleanup alarm and may be evicted between requests.
Its SQLite records survive eviction and redeployment. Do not change the Durable
Object class/binding, stable `pilot7-review-v1` object name, or delete migration
history to rename the Worker. These identify the existing state.

OAuth state is random, consumed in a SQLite transaction, and expires after five
minutes. Reviewer sessions last at most one hour, bounded by GitHub's token
expiry. The browser holds only an opaque session ID in memory. GitHub access
tokens remain in Durable Object storage and never enter browser storage or URLs.
Cleanup alarms physically delete expired state, tokens and submission results;
sign out immediately removes the active session. Users can revoke the App in
GitHub settings. Treat the Durable Object's stored data as credentials.

A per-object request queue covers the external GitHub writes, including thread
creation. Submission intent is written durably before posting; the confirmed
result is stored afterward. Repeated clicks and retries use the same submission
key. After a lost response or a cold start, the service checks for the exact
previous comment by that reviewer before issuing another write. Tests restart
the actual Workers runtime against the same SQLite files to verify this behavior.

A Worker interruption during an external request cannot make GitHub and SQLite
one atomic transaction. The retained intent and exact-comment lookup recover
ambiguous writes. Check the discussion before retrying after an unexplained
failure. Editing an assessment intentionally creates a new submission; reloading
starts a new browser submission session.

## Behavior and limits

- Submission is an explicit user action; sign-in completes that pending action.
  The form is disabled while submitting. Errors retain the automatic local draft.
  A confirmed comment link appears only after a successful GitHub response or
  recovery of the previously authored comment. Copy/paste remains a fallback.
- The service posts only to the configured repository/category, catalog study,
  and dataset term used by giscus. It finds the exact existing thread and creates
  one only if missing. The body retains reviewer-supplied decisions, finding,
  evidence revision, check IDs and a reproducible link. It does not validate
  clinical evidence or approve a finding.
- The popup result is restricted to SITE_URL's origin, and the dashboard checks
  origin, popup source and request nonce. CORS permits that site origin only.
  Requests use a bearer session, without ambient cookies. Responses are not cached.
  Worker observability is disabled in the template to avoid retaining OAuth
  callback query strings. Do not enable request/query logging without redaction.
- JSON requests are streamed with a 24 KB cap. Review text is limited to 10,000
  characters. There are caps of 1,000 pending sign-ins, 1,000 sessions, and 100
  submissions per session. Add Cloudflare per-IP rate limits for a public launch.
  GitHub rate limits and revoked/insufficient App or reviewer permissions surface
  as errors. The single object serializes submissions, appropriate for this
  low-volume review site. Higher throughput requires a deliberate sharding design.

## Local checks

```bash
npm ci
npm test
```

This builds the Worker without deploying it and runs API, SQLite expiry, and
Miniflare/workerd tests, including cold-start persistence and concurrent retries.
From the repository root, run the dashboard checks too:

```bash
node --test .github/tests/dashboard/*.test.js
python .github/tests/dashboard/direct_submission_browser.py
```

For local manual development, `npm run dev` runs Wrangler with local persistent
SQLite. Put test credentials in ignored `.dev.vars`, override SITE_URL and
SERVICE_URL to the actual localhost origins, and register the matching App
callback. Only localhost/127.0.0.1 may use HTTP. `npm start` provides an optional
Node-only adapter for debugging; it uses temporary in-memory state and is not
the production deployment.
