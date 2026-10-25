#!/usr/bin/env python3
"""Exercise complete real-data review bundles in a browser, with no write actions."""
import argparse
import csv
import gzip
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
PREFIX = "/review/project"


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith(PREFIX + "/"):
            self.send_error(404)
            return
        super().do_GET()

    def translate_path(self, path):
        return super().translate_path(path.removeprefix(PREFIX))

    def log_message(self, *_args):
        pass


def capture(page, directory, name):
    if directory:
        directory.mkdir(parents=True, exist_ok=True)
        page.evaluate("document.activeElement.blur();window.scrollTo(0,0)")
        page.screenshot(
            path=str(directory / name), full_page=True, animations="disabled"
        )


def check(browser, base, site_dir, screenshots):
    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    context.route(
        "https://giscus.app/client.js",
        lambda route: route.fulfill(body="", content_type="application/javascript"),
    )
    errors = []
    context.on("weberror", lambda e: errors.append(str(e.error)))
    catalog = json.loads(
        (site_dir / "assets/review-data/cdiscpilot01/catalog.json").read_text()
    )
    page = context.new_page()
    study = base + "/studies/cdiscpilot01/"
    page.goto(study)
    expect(page.locator("#output-table tbody tr")).to_have_count(3)
    expect(page.locator("#subject-summary")).to_contain_text(
        f'3 / {len(catalog["subjects"])}'
    )
    assert page.locator(".spec-line").count() > 700
    pane = page.locator(".review-workbench").bounding_box()
    assert (
        pane["y"] + pane["height"] <= 1000
    ), "all three panes fit one desktop viewport"
    page.locator('#input-table button[data-node="DM.ARM"]').click()
    expect(page.locator('#output-table th[data-node="output.TRT01P"]')).to_have_class(
        "node-related"
    )
    assert page.locator('[data-line-node="spec.TRT01P"].node-related').count() >= 4
    capture(page, screenshots, "dataset-workspace.png")
    page.locator('#output-table button[data-node="output.TRT01P"]').click()
    expect(page.locator('#input-table th[data-node="DM.ARM"]')).to_have_class(
        "node-related"
    )
    page.locator('button[data-node="spec.TRT01P"]').first.click()
    expect(page.locator('#output-table th[data-node="output.TRT01P"]')).to_have_class(
        "node-related"
    )
    page.locator("#spec-resizer").focus()
    page.keyboard.press("ArrowRight")
    expect(page.locator("#spec-resizer")).to_have_attribute("aria-valuenow", "38")
    page.get_by_role("button", name="Clear highlight", exact=True).click()
    expect(page.locator(".node-selected")).to_have_count(0)

    page.locator("#subject-summary").click()
    page.get_by_role("button", name="Select all", exact=True).click()
    total = catalog["tables"][catalog["datasets"][0]["output"]]["rows"]
    expect(page.locator("#output-footer")).to_contain_text(f"of {total} selected rows")
    expect(page.locator("#output-table tbody tr")).to_have_count(40)
    page.locator("#subject-summary").click()
    page.get_by_role("button", name="Next output rows", exact=True).click()
    expect(page.locator("#output-footer")).to_contain_text(f"41-80 of {total}")
    with page.expect_download() as download:
        page.locator("#output-actions [data-export]").click()
    with Path(download.value.path()).open(newline="") as handle:
        rows = list(csv.reader(handle))
    assert (
        len(rows) == total + 1 and "USUBJID" in rows[0]
    ), "CSV exports all selected rows, not only the displayed page"
    page.locator("#output-select").select_option("reference")
    expect(page.locator("#output-footer")).to_contain_text(f"of {total} selected rows")
    page.locator("#subject-summary").click()
    page.locator('#subject-picker [data-subject-count="0"]').click()
    expect(page.locator("#output-table")).to_contain_text("No subjects selected")
    page.get_by_role("button", name="First 10", exact=True).click()
    expect(page.locator("#subject-summary")).to_contain_text("10 /")
    page.get_by_role("button", name="First 3", exact=True).click()
    page.locator("#subject-search").fill(catalog["subjects"][0])
    expect(page.locator("[data-subject-option]:visible")).to_have_count(1)
    page.locator("[data-subject-option]:visible input").uncheck()
    expect(page.locator("#subject-summary")).to_contain_text("2 /")
    page.get_by_role("button", name="First 3", exact=True).click()
    page.locator("#subject-summary").click()
    page.locator("#record-search").fill(catalog["subjects"][0])
    expect(page.locator("#output-table tbody tr")).to_have_count(1)
    page.locator('#output-table button[data-node="output.AGE"]').click()
    bookmark = page.url
    page.reload()
    expect(page.locator("#output-table tbody tr")).to_have_count(1)
    expect(page.locator("#record-search")).to_have_value(catalog["subjects"][0])
    expect(page.locator("#output-select")).to_have_value("reference")
    expect(page.locator('#output-table th[data-node="output.AGE"]')).to_have_class(
        "node-selected"
    )
    shared = context.new_page()
    shared.goto(bookmark)
    expect(shared.locator("#output-table tbody tr")).to_have_count(1)
    shared.close()
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.get_by_role("button", name="Copy view link", exact=True).click()
    expect(page.locator("#review-toast")).to_contain_text("copied")
    assert page.evaluate("navigator.clipboard.readText()") == page.url
    page.evaluate(
        'Object.defineProperty(navigator,"clipboard",{value:{writeText:async()=>{throw Error("Denied")}}})'
    )
    page.get_by_role("button", name="Copy view link", exact=True).click()
    expect(page.locator("#share-url")).to_have_value(page.url)
    page.locator("#record-search").fill("not present in these records")
    expect(page.locator("#output-table")).to_contain_text(
        "No records for these subjects"
    )
    page.locator("#record-search").fill("")

    page.locator("#dataset-select").select_option("ADAE")
    expect(page.locator("#input-select")).to_have_value("AE")
    expect(page.locator("#output-table tbody tr")).not_to_have_count(0)
    page.locator("#output-select").select_option("derived")
    page.locator('#output-table button[data-node="output.ASTDT"]').click()
    expect(page.locator('#input-table th[data-node="AE.AESTDTC"]')).to_have_class(
        "node-related"
    )
    page.locator('.review-tabs [data-view="findings"]').click()
    expect(page.locator(".finding-card")).not_to_have_count(0)
    capture(page, screenshots, "documentation-findings.png")
    page.locator("#finding-search").fill("imputation")
    expect(page.locator(".finding-card")).to_have_count(1)
    page.locator(".finding-card summary").click()
    expect(page.locator(".finding-card blockquote")).to_contain_text("imputed")
    page.get_by_role("button", name="Open evidence in workspace", exact=True).click()
    expect(page.locator(".evidence-drawer")).to_be_visible()
    expect(page.locator(".evidence-drawer")).to_contain_text("dataguide.pdf")
    expect(page.locator('#output-table th[data-node="output.ASTDT"]')).to_have_class(
        "node-related"
    )
    cited = (
        page.locator(".evidence-drawer")
        .get_by_role("link", name="Open cited source")
        .get_attribute("href")
    )
    assert PREFIX in cited and "#page-" in cited
    assert page.request.get(cited.split("#")[0]).status == 200
    capture(page, screenshots, "source-evidence.png")
    page.get_by_role("button", name="Close source evidence").click()
    expect(page.locator(".evidence-drawer")).to_have_count(0)
    page.locator('.review-tabs [data-view="comments"]').click()
    expect(page.locator("#comments-host script")).to_have_attribute(
        "data-repo", "elong0527/yamaa"
    )
    expect(page.locator("#comments-host script")).to_have_attribute(
        "data-term", "pilot7/studies/cdiscpilot01/ADAE"
    )
    expect(page.locator(".comment-fallback a")).to_have_count(2)
    page.locator('.review-tabs [data-view="materials"]').click()
    expect(page.locator(".material-card")).not_to_have_count(0)
    for anchor in page.locator(".material-card a").all():
        url = anchor.get_attribute("href")
        if url.startswith(base):
            assert page.request.get(url).status == 200, url
    page.locator('.review-tabs [data-view="overview"]').click()
    expect(page.locator(".overview-table tbody tr")).to_have_count(10)
    capture(page, screenshots, "overview.png")

    # Native instant navigation, CSV planning inputs, and subject-independent lookups.
    page.locator('.md-nav--primary a[href*="submission-pilot3"]').click()
    expect(page.locator("#study-dashboard")).to_have_attribute(
        "data-study", "submission-pilot3"
    )
    expect(page.locator("#output-table tbody tr")).to_have_count(3)
    page.locator("#dataset-select").select_option("ADADAS")
    expect(page.locator('#input-select option[value="AW"]')).to_have_count(1)
    page.locator("#input-select").select_option("AW")
    expect(page.locator("#input-footer")).to_contain_text("subject-independent lookup")
    expect(page.locator("#input-table tbody tr")).to_have_count(4)
    page.locator("#input-select").select_option("PLAN")
    expect(page.locator("#input-actions a")).to_contain_text("CSV")
    page.go_back()
    page.go_forward()
    expect(page.locator("#input-select")).to_have_value("PLAN")

    for width in [375, 768, 1600]:
        page.set_viewport_size({"width": width, "height": 1000})
        for view in ["datasets", "findings", "materials"]:
            page.goto(study + f"#cdiscpilot01/{view}/ADAE")
            expect(page.locator(".review-tabs .active")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (
                width,
                view,
            )
            if width == 375 and view == "datasets":
                page.locator("#subject-summary").click()
                box = page.locator(".subject-popover").bounding_box()
                assert box["x"] >= 0 and box["x"] + box["width"] <= width
                page.locator("[data-close-subjects]").click()
                expect(page.locator("#subject-picker")).not_to_have_attribute("open", "")
                capture(page, screenshots, "mobile-workspace.png")
    page.goto(study + "#cdiscpilot01/datasets/ADSL?focus=output.TRT01P")
    expect(page.locator("#output-table th.node-selected")).to_have_count(1)
    page.evaluate('document.body.dataset.mdColorScheme="slate"')
    capture(page, screenshots, "dark-workspace.png")
    # Invalid state and HTML-like search text must not inject markup.
    page.goto(
        study
        + "#cdiscpilot01/datasets/UNKNOWN?focus=UNKNOWN&subjects=UNKNOWN&rowSearch=%3Cimg%20src=x%3E"
    )
    expect(page.locator("#dataset-select")).to_have_value("ADSL")
    expect(page.locator("#output-table")).to_contain_text("No subjects selected")
    expect(page.locator("#record-search")).to_have_value("<img src=x>")
    expect(page.locator("#view-content img")).to_have_count(0)
    page.goto(base + "/studies/")
    expect(page.locator(".study-card")).to_have_count(3)
    page.goto(base + "/studies/submission-pilot6/")
    expect(page.locator("#study-dashboard")).to_contain_text(
        "no validated artifact bundle"
    )
    assert not errors, errors
    context.close()

    # An unavailable chunk must be explicit and retryable, not a false empty result.
    failure_context = browser.new_context()
    failure = failure_context.new_page()
    attempts = []

    def once(route):
        if not attempts:
            attempts.append(True)
            route.fulfill(status=503, body="Unavailable")
        else:
            route.continue_()

    failure.route("**/cdiscpilot01/tables/t000/0.json.gz", once)
    failure.goto(study)
    expect(failure.locator("#input-table .error-state")).to_be_visible()
    failure.locator("#input-table #retry-data").click()
    expect(failure.locator("#input-table tbody tr")).to_have_count(3)
    failure_context.close()

    # Fetch may expose already-decoded bytes when a host sets Content-Encoding.
    decoded_context = browser.new_context()
    decoded = decoded_context.new_page()
    chunk = site_dir / "assets/review-data/cdiscpilot01/tables/t000/0.json.gz"
    decoded.route(
        "**/cdiscpilot01/tables/t000/0.json.gz",
        lambda route: route.fulfill(
            body=gzip.decompress(chunk.read_bytes()), content_type="application/json"
        ),
    )
    decoded.goto(study)
    expect(decoded.locator("#input-table tbody tr")).to_have_count(3)
    decoded_context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site-dir", type=Path, default=ROOT / ".build/study-dashboard-preview/site"
    )
    parser.add_argument("--browser-path")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if not (args.site_dir / "assets/review-data/index.json").is_file():
        parser.error("Build real review artifacts first.")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(PreviewHandler, directory=str(args.site_dir.resolve())),
    )
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser_path)
            try:
                check(
                    browser,
                    f"http://127.0.0.1:{server.server_port}{PREFIX}",
                    args.site_dir,
                    args.screenshots,
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    print(
        "Browser checks passed: complete subjects and CSV, bidirectional lineage, source evidence, shared links, comments configuration, instant navigation, CSV lookups, responsive layouts, dark mode, and retryable data errors. Comment posting/authentication is not exercised."
    )


if __name__ == "__main__":
    main()
