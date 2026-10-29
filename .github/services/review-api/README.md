# Direct GitHub review submission

The dashboard stays on GitHub Pages. This optional Node 22+ service handles
GitHub App user sign-in and posts the form to the existing giscus dataset
thread as that user. It uses no database or npm dependencies. Do not put a
client secret, GitHub token, or service bearer token in the dashboard config.

## Activate

1. Register a GitHub App with **Discussions: Read and write** and the default
   Metadata permission. Enable user authorization and configure its callback as
   `https://YOUR-SERVICE/auth/callback`. Disable expiring user tokens only if your
   organization requires it; the service supports expiring tokens without a
   refresh token. Do not request broad OAuth App scopes or use a bot token.
2. Install the App on `elong0527/yamaa`, the existing discussion repository in
   `.github/dashboard.json`. Reviewers authorize the App with their own GitHub
   accounts; GitHub still enforces their access to that repository. The service
   uses the App's client ID and client secret, not an installation/private-key
   token, to obtain a user access token.
3. Deploy this repository at the reviewed revision to one persistent Node
   instance behind HTTPS. Set these environment variables through the host's
   secret/configuration settings:

   ```text
   SITE_URL=https://rconsortium.github.io/submissions-pilot7-synthetic-data/
   SERVICE_URL=https://YOUR-SERVICE
   GITHUB_CLIENT_ID=<GitHub App client ID>
   GITHUB_CLIENT_SECRET=<secret stored only on the service host>
   PORT=8080
   ```

   Run `node .github/services/review-api/server.js` from the repository root.
   `GET /health` returns readiness. Use the included Dockerfile with the
   repository root as build context if your host accepts containers.
4. Set `comments.direct_submission_url` in `.github/dashboard.json` to the
   deployed HTTPS origin and publish the site. It must have no path or query.
   An empty value keeps the existing copy/paste workflow. This PR intentionally
   supplies no guessed service domain or credentials.
5. Verify the complete flow with a test reviewer: select both decisions, enter
   comments, select **Submit review to GitHub**, authorize in the popup, and
   follow **View GitHub comment**. Check that the comment is attributed to the
   reviewer and appears in the existing dataset discussion. No live comments
   are posted by the automated tests.

Local development accepts HTTP only for localhost/127.0.0.1. Both SITE_URL and
SERVICE_URL must match the actual browser origins and the registered callback.
For a local site, include its project path in SITE_URL so review links stay valid.

## Behavior and limits

- Submission is an explicit user action. Sign-in completes that pending action;
  it never publishes unrelated drafts. The form is disabled during the request.
  Failures preserve the automatic browser draft. A copy/paste fallback remains.
- Successful submission displays a link only after GitHub confirms the comment.
  The body records the study, finding, decisions, evidence revision, check IDs,
  and a reproducible finding link. These are reviewer-supplied context, not
  a server validation of clinical evidence or an approval of the finding.
- Only the configured repository/category and catalog studies are supported.
  Thread lookup matches the exact existing giscus term and category. Missing
  threads are created using the same convention; no destination comes from the
  client. Publication does not move discussions to a different repository.
- OAuth state is random, expires after five minutes, and is consumed once.
  The popup sends its result only to SITE_URL's origin. The dashboard validates
  the popup source, service origin and request nonce. Access tokens stay on
  the service; short-lived opaque session IDs stay in browser memory. They are
  never stored in browser storage or URLs. Sign out clears the service session;
  users can revoke the App authorization through GitHub settings.
- CORS permits only the configured site origin. Authenticated requests use a
  bearer session and no ambient cookies. Responses are not cached. Configure
  your reverse proxy to enforce HTTPS, request timeouts and an appropriate
  per-IP request limit, and redact OAuth callback query strings from logs.
  Run exactly one service replica: state, one-hour sessions, submission results,
  and thread locks are in process memory. A restart requires sign-in again.
  Multiple replicas require shared transactional state and locks before scaling.
- Repeated clicks/retries reuse an idempotency key. The service serializes each
  thread and checks for the exact prior comment by that reviewer before writing,
  including after an ambiguous network failure. Editing the assessment starts
  a new submission. Reloading the page starts a new browser submission session;
  check the discussion before repeating a review after a reload or service restart.
- The service caps JSON requests at 24 KB, pending logins/sessions at 1,000,
  and submissions at 100 per sign-in. Review text is limited to 10,000 characters.
  GitHub rejects revoked tokens or insufficient App/reviewer permissions.

Run `node --test .github/services/review-api/*.test.js` for service checks and
`python .github/tests/dashboard/direct_submission_browser.py` for the browser
flow with intercepted GitHub traffic. The dedicated PR workflow runs both.
