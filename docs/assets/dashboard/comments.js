/** Components read the live application context at render time. */
export function createComments(ctx) {
  function commentsView() {
    const { model, index, state, esc, dataset, link } = ctx;
    const c = index.comments;
    return `<div class="section-heading"><div><h2 id="comments-heading">Review comments</h2><p>Discuss ${esc(model.title)} / ${state.dataset}. Attach the current view link so reviewers can reproduce your context.</p></div><button class="button" id="copy-comment-context">Copy review context</button></div><div class="coverage-note">Comments are saved in <strong>${esc(c.repo)} GitHub Discussions</strong>, using a separate Pilot 7 thread for each dataset. GitHub sign-in is required to post. The static dashboard does not store comments locally.</div><div id="share-fallback" hidden><label>Copy review context<textarea id="share-url" readonly rows="6"></textarea></label></div><div id="comments-host"></div><p class="comment-fallback">If the embedded discussion is unavailable, ${link(c.discussion_url, "open GitHub Discussions")} or ${link(issueUrl(), "open a Pilot 7 review issue")}.</p>`;
  }
  function issueUrl() {
    const { model, index, state, dataset } = ctx;
    const title = `[Dashboard review] ${model.id} ${state.dataset}${state.focus ? " / " + state.focus : ""}`;
    return `${index.comments.issue_url}?title=${encodeURIComponent(title)}&body=${encodeURIComponent(commentContext())}`;
  }
  function commentContext() {
    const { model, state, dataset, link } = ctx;
    return `Study: ${model.id}\nDataset: ${state.dataset}\nSelection: ${state.focus || "none"}\nSubjects: ${state.subjects.length === model.subjects.length ? "all" : state.subjects.join(", ")}\nSource revision: ${model.revision}\nReview link: ${location.href}\n\nObservation:\n\nSupporting evidence:\n`;
  }
  function loadComments() {
    const { model, index, state, byId, dataset, link } = ctx;
    const c = index.comments,
      host = byId("comments-host");
    if (!host) return;
    if (!c.repo_id || !c.category_id) {
      host.innerHTML =
        "<p>GitHub discussion configuration is incomplete. Use the review-issue link below.</p>";
      return;
    }
    const script = document.createElement("script");
    script.src = "https://giscus.app/client.js";
    script.async = true;
    script.crossOrigin = "anonymous";
    for (const [key, value] of Object.entries({
      repo: c.repo,
      "repo-id": c.repo_id,
      category: c.category,
      "category-id": c.category_id,
      mapping: "specific",
      term: c.term_prefix + model.id + "/" + state.dataset,
      strict: "1",
      "reactions-enabled": "1",
      "emit-metadata": "0",
      "input-position": "top",
      theme: document.body.dataset.mdColorScheme === "slate" ? "dark" : "light",
      lang: "en",
      loading: "lazy",
    }))
      script.setAttribute("data-" + key, value);
    host.append(script);
  }

  return { commentsView, issueUrl, commentContext, loadComments };
}
