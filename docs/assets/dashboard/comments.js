/** Components read the live application context at render time. */
export function createComments(ctx) {
  function commentsView() {
    const { model, index, state, esc, link } = ctx;
    const c = index.comments;
    return `<div class="section-heading"><div><h2 id="comments-heading">Review comments</h2><p>Discuss ${esc(model.title)} / ${state.dataset}. Attach the current view link so reviewers can reproduce your context.</p></div></div><div id="comments-host"></div><p class="comment-fallback">If the embedded discussion is unavailable, ${link(c.discussion_url, "open GitHub Discussions")} or ${link(issueUrl(), "open a Pilot 7 review issue")}.</p>`;
  }
  function issueUrl() {
    const { model, index, state } = ctx;
    const title = `[Dashboard review] ${model.id} ${state.dataset}${state.focus ? " / " + state.focus : ""}`;
    return `${index.comments.issue_url}?title=${encodeURIComponent(title)}&body=${encodeURIComponent(commentContext())}`;
  }
  function commentContext() {
    const { model, state } = ctx;
    return `Study: ${model.id}\nDataset: ${state.dataset}\nSelection: ${state.focus || "none"}\nSubjects: ${state.subjects.length === model.subjects.length ? "all" : state.subjects.join(", ")}\nCompared outputs: ${[state.dataset, ...state.outputs].join(", ")}\nSource revision: ${model.revision}\nReview link: ${location.href}\n\nObservation:\n\nSupporting evidence:\n`;
  }
  function loadComments() {
    const { model, index, state, byId } = ctx;
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
    script.addEventListener("error", () => {
      const message = document.createElement("p");
      message.textContent = "GitHub comments could not load. Use the GitHub Discussions link to publish your review.";
      host.append(message);
    });
    host.append(script);
    // Reapply the current term after lazy loading or moving the widget.
    host.addEventListener("load", () => syncComments(host), true);
  }

  function syncComments(host) {
    const script = host.querySelector("script[data-term]"),
      frame = host.querySelector("iframe.giscus-frame");
    if (script && frame?.contentWindow) frame.contentWindow.postMessage({ giscus: { setConfig: {
      term: script.dataset.term,
      theme: document.body.dataset.mdColorScheme === "slate" ? "dark" : "light",
    } } }, "https://giscus.app");
  }

  function attachComments(target, dataset) {
    const host = ctx.byId("comments-host");
    if (!host) {
      target.textContent = "The comment widget is unavailable. Use the GitHub Discussions link below.";
      return () => {};
    }
    const placeholder = document.createElement("p"),
      script = host.querySelector("script[data-term]"),
      originalTerm = script?.dataset.term;
    placeholder.textContent = "GitHub comments are open in the review dialog. Close it to return to this discussion.";
    host.before(placeholder);
    if (script) script.dataset.term = ctx.index.comments.term_prefix + ctx.model.id + "/" + dataset;
    // giscus supports one container per page. Reuse it instead of a second embed.
    target.append(host);
    syncComments(host);
    return () => {
      if (script) script.dataset.term = originalTerm;
      if (placeholder.isConnected) placeholder.replaceWith(host);
      else host.remove();
      syncComments(host);
    };
  }

  return { commentsView, issueUrl, loadComments, attachComments };
}
