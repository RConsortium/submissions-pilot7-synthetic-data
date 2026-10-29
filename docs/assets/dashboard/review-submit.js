/** Tokens stay in memory; GitHub credentials never enter the static site. */
export function createReviewSubmission(config, browser = window) {
  if (!config.direct_submission_url) return null;
  const base = new URL(config.direct_submission_url);
  if ((base.protocol !== 'https:' && !(base.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(base.hostname))) || base.pathname !== '/' || base.search || base.hash || base.username || base.password)
    throw Error('Invalid review submission service URL.');
  let session = '', login = '', signingIn = null;
  const attempts = new Map();
  async function api(path, data) {
    let response;
    try {
      response = await browser.fetch(new URL(path, base), {
        method: 'POST', credentials: 'omit', referrerPolicy: 'no-referrer',
        headers: { 'Content-Type': 'application/json', ...(session ? { Authorization: `Bearer ${session}` } : {}) },
        body: JSON.stringify(data), signal: AbortSignal.timeout(90000),
      });
    } catch { throw Error('The review service could not be reached. Your draft is retained. Check the discussion before retrying.'); }
    const result = await response.json();
    if (response.status === 401) { session = ''; login = ''; }
    if (!response.ok) throw Error(result.error || 'Your review could not be submitted. Your draft is retained.');
    return result;
  }
  function signIn() {
    if (session) return Promise.resolve(login);
    if (signingIn) return signingIn;
    const popup = browser.open('about:blank', 'pilot7-github-signin', 'popup,width=700,height=750');
    if (!popup) return Promise.reject(Error('Allow the GitHub sign-in popup and try again. Your draft is retained.'));
    const nonce = browser.crypto.randomUUID();
    signingIn = new Promise((resolve, reject) => {
      let timer, closed, finished = false;
      const finish = (error, user) => {
        if (finished) return;
        finished = true;
        browser.removeEventListener('message', receive);
        browser.clearTimeout(timer); browser.clearInterval(closed);
        popup.close(); signingIn = null;
        if (error) reject(error); else resolve(user);
      };
      const receive = event => {
        const data = event.data;
        if (event.origin !== base.origin || event.source !== popup || data?.type !== 'pilot7-github-auth' || data.nonce !== nonce) return;
        if (typeof data.error === 'string') { finish(Error(data.error)); return; }
        if (!/^[a-f0-9]{64}$/.test(data.session || '') || !/^[a-z0-9-]+$/i.test(data.login || '')) return;
        session = data.session; login = data.login; finish(null, login);
      };
      browser.addEventListener('message', receive);
      timer = browser.setTimeout(() => finish(Error('GitHub sign-in expired. Try again. Your draft is retained.')), 300000);
      closed = browser.setInterval(() => { if (popup.closed) finish(Error('GitHub sign-in was cancelled. Your draft is retained.')); }, 500);
      api('/auth/start', { nonce }).then(result => {
        const url = new URL(result.url);
        if (url.origin !== 'https://github.com' || url.pathname !== '/login/oauth/authorize') throw Error('Invalid GitHub sign-in response.');
        if (!popup.closed) popup.location.href = url.href;
      }).catch(error => finish(error));
    });
    return signingIn;
  }
  async function submit(model, issue, review) {
    if (!session) throw Error('Sign in with GitHub before submitting.');
    const payload = {
      model: { id: model.id, revision: model.revision },
      issue: { id: issue.id, dataset: issue.dataset, variable: issue.variable || '', title: issue.title, check_ids: issue.check_ids },
      review: { agreement: review.agreement, criticality: review.criticality, comment: review.comment },
    };
    const signature = JSON.stringify(payload);
    if (!attempts.has(signature)) attempts.set(signature, browser.crypto.randomUUID());
    const result = await api('/reviews', { ...payload, requestId: attempts.get(signature) });
    if (typeof result.url !== 'string' || !result.url.startsWith(`https://github.com/${config.repo}/discussions/`))
      throw Error('GitHub did not confirm a comment link. Check the discussion before retrying.');
    return result;
  }
  async function signOut() {
    try { if (session) await api('/logout', {}); }
    finally { session = ''; login = ''; }
  }
  return { signIn, submit, signOut, get login() { return login; } };
}
