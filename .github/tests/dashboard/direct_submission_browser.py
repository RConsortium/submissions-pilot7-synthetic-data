#!/usr/bin/env python3
"""Exercise direct submission with intercepted OAuth/API traffic, never real posts."""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[3]
SERVICE = "https://reviews.example.org"
COMMENT = "https://github.com/elong0527/yamaa/discussions/42#discussioncomment-123"


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def check(browser, base):
    context = browser.new_context()
    auth = {}
    posts = []
    mode = {"fail": False}
    def service(route):
        request = route.request
        headers = {"Access-Control-Allow-Origin": base, "Access-Control-Allow-Headers": "Authorization, Content-Type"}
        if request.method == "OPTIONS":
            route.fulfill(status=204, headers=headers)
        elif request.url.endswith("/auth/start"):
            auth["nonce"] = request.post_data_json["nonce"]
            route.fulfill(json={"url": "https://github.com/login/oauth/authorize?client_id=test"}, headers=headers)
        elif request.url.endswith("/auth/callback"):
            data = {"type": "pilot7-github-auth", "nonce": auth["nonce"], "session": "a" * 64, "login": "reviewer"}
            route.fulfill(content_type="text/html", body=f"<script>opener.postMessage({json.dumps(data)},{json.dumps(base)});window.close()</script>")
        elif request.url.endswith("/reviews"):
            assert request.headers["authorization"] == "Bearer " + "a" * 64
            posts.append(request.post_data_json)
            if mode["fail"]:
                route.fulfill(status=502, json={"error": "GitHub could not complete the review. Your draft is retained."}, headers=headers)
            else:
                route.fulfill(json={"url": COMMENT, "login": "reviewer"}, headers=headers)
        else:
            route.fulfill(json={"ok": True}, headers=headers)
    context.route(SERVICE + "/**", service)
    context.route("https://github.com/login/oauth/authorize**", lambda route: route.fulfill(status=302, headers={"Location": SERVICE + "/auth/callback"}))
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base + "/docs/assets/dashboard/")
    page.evaluate("""async service => {
      document.body.innerHTML = '<main id="root"></main>';
      const {createTraceReview} = await import('./trace-review.js');
      const issue = {id:'cdiscpilot01:ADAE.FLAG.test',dataset:'ADAE',variable:'FLAG',title:'Test finding',kind:'conflict',summary:'Browser fixture',review:'needs_review',check_ids:[],trace:[],impact:{subjects:[],subject_count:0}};
      const ctx = {root:()=>document.querySelector('#root'),model:{id:'cdiscpilot01',title:'Pilot',revision:'a'.repeat(40)},report:{review:{schema_version:1,issues:[issue],checks:[],evidence:[]}},index:{comments:{direct_submission_url:service,discussion_url:'https://github.com/elong0527/yamaa/discussions',repo:'elong0527/yamaa'}}};
      window.trace = createTraceReview(ctx,{attachComments:()=>()=>{}});
      window.openTrace = ()=>trace.open(issue.id); openTrace();
    }""", SERVICE)
    dialog = page.locator("dialog")
    submit = dialog.get_by_role("button", name="Submit review to GitHub", exact=True)
    submit.click()
    expect(dialog.locator(".trace-review-feedback")).to_contain_text("Choose both")
    assert not posts
    dialog.get_by_role("radio", name="Agree", exact=True).check()
    dialog.get_by_role("radio", name="Not critical", exact=True).check()
    dialog.locator("#trace-review-comment").fill("A review without copying or pasting")
    submit.click()
    expect(dialog.get_by_role("link", name="View GitHub comment")).to_have_attribute("href", COMMENT)
    assert len(posts) == 1
    assert posts[0]["review"]["comment"] == "A review without copying or pasting"
    assert posts[0]["issue"]["dataset"] == "ADAE"
    expect(submit).to_be_enabled()
    dialog.locator("#trace-review-comment").fill("Changed assessment")
    # An error keeps the draft and retry reuses the same idempotency key.
    mode["fail"] = True
    submit.click()
    expect(dialog.locator(".trace-review-feedback")).to_contain_text("Your draft is retained")
    expect(dialog.get_by_role("link", name="View GitHub comment")).to_have_count(0)
    expect(dialog.locator("#trace-review-comment")).to_be_enabled()
    mode["fail"] = False
    submit.click()
    expect(dialog.get_by_role("link", name="View GitHub comment")).to_be_visible()
    assert posts[-1]["requestId"] == posts[-2]["requestId"]
    dialog.get_by_role("button", name="Sign out @reviewer", exact=True).click()
    expect(dialog.get_by_role("button", name="Sign out @reviewer", exact=True)).to_be_hidden()
    page.evaluate("window.open=()=>null")
    submit.click()
    expect(dialog.locator(".trace-review-feedback")).to_contain_text("Allow the GitHub sign-in popup")
    page.evaluate("trace.close();openTrace()")
    expect(dialog.locator("#trace-review-comment")).to_have_value("Changed assessment")
    assert not errors, errors
    context.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser-path")
    args = parser.parse_args()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser_path, headless=True, args=["--no-sandbox"])
            check(browser, f"http://127.0.0.1:{server.server_port}")
            browser.close()
    finally:
        server.shutdown()
    print("Direct submission browser checks passed (mock GitHub; no real comments posted).")
