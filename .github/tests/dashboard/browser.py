#!/usr/bin/env python3
"""Exercise complete real-data review bundles in a browser, with no write actions."""
import argparse
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
        lambda r: r.fulfill(body="", content_type="application/javascript"),
    )
    errors = []
    context.on("weberror", lambda e: errors.append(str(e.error)))
    catalog = json.loads(
        (site_dir / "evidence/dashboard/cdiscpilot01/catalog.json").read_text()
    )
    adsl = next(d for d in catalog["datasets"] if d["name"] == "ADSL")
    dm = next(i["table"] for i in adsl["inputs"] if i["alias"] == "DM")
    ex = next(i["table"] for i in adsl["inputs"] if i["alias"] == "EX")
    page = context.new_page()
    study = base + "/studies/cdiscpilot01/"
    page.goto(study)
    expect(page.locator("#output-table tbody tr")).to_have_count(3)
    expect(page.locator("#subject-summary")).to_contain_text("3 /")
    expect(page.locator(".md-sidebar--primary")).not_to_be_visible()
    assert page.locator("#study-dashboard").bounding_box()["width"] >= 0.95 * 1600
    expect(page.locator(".input-group h3")).to_have_text("DM - Demographics")
    expect(
        page.locator("#copy-view, #wide-mode, .provenance, [data-export]")
    ).to_have_count(0)
    expect(
        page.locator(
            '.review-tabs [data-view="comments"], .review-tabs [data-view="findings"]'
        )
    ).to_have_count(0)
    source = page.get_by_role("link", name="Study source", exact=True)
    assert (
        source.get_attribute("href")
        == f'https://github.com/RConsortium/submissions-pilot7-synthetic-data/tree/{catalog["revision"]}/cdiscpilot01'
    )
    title = page.locator(".review-hero h1").bounding_box()
    links = page.locator(".hero-actions").bounding_box()
    assert title["x"] + title["width"] < links["x"] < title["x"] + title["width"] + 50
    assert abs(links["y"] - title["y"]) < 15
    # Outside clicks, focus changes and Escape dismiss selection popovers.
    page.locator("#subject-summary").click()
    page.locator("#subject-search").fill(catalog["subjects"][0])
    expect(page.locator("[data-subject-option]:visible")).to_have_count(1)
    page.locator("#record-search").click()
    expect(page.locator("#subject-picker")).not_to_have_attribute("open", "")
    page.locator("#subject-summary").click()
    page.keyboard.press("Escape")
    expect(page.locator("#subject-picker")).not_to_have_attribute("open", "")
    page.locator("#subject-summary").click()
    page.locator("#subject-search").fill("")
    page.locator("#record-search").focus()
    expect(page.locator("#subject-picker")).not_to_have_attribute("open", "")
    # Independent input/output page sizes, original ordering, and all subjects.
    page.locator("#subject-summary").click()
    page.get_by_role("button", name="Select all", exact=True).click()
    page.locator("#subject-summary").click()
    expect(page.locator("#output-table tbody tr")).to_have_count(10)
    expect(page.locator("#input-table tbody tr")).to_have_count(10)
    assert page.locator("#output-table tbody th").all_text_contents() == [
        str(i) for i in range(1, 11)
    ]
    for size in [25, 50, 100]:
        page.get_by_label("DM input rows per page", exact=True).select_option(str(size))
        expect(page.locator("#input-table tbody tr")).to_have_count(size)
        page.get_by_label("ADSL output rows per page", exact=True).select_option(
            str(size)
        )
        expect(page.locator("#output-table tbody tr")).to_have_count(size)
    page.get_by_label("ADSL output rows per page", exact=True).select_option("25")
    expect(page.locator("#input-table tbody tr")).to_have_count(100)
    page.get_by_role("button", name="Next ADSL output rows", exact=True).click()
    expect(page.locator("#output-footer")).to_contain_text("26-50 of 254")
    assert page.locator("#output-table tbody th").all_text_contents() == [
        str(i) for i in range(26, 51)
    ]
    page.locator("#output-select").select_option("reference")
    expect(page.locator("#output-table tbody tr")).to_have_count(25)
    page.locator("#output-select").select_option("derived")
    for name in ["DM input rows per page", "ADSL output rows per page"]:
        page.get_by_label(name, exact=True).select_option("10")
    # Specification, area split and table columns resize with keyboard and pointer.
    before = page.locator(".spec-pane").bounding_box()["width"]
    page.locator("#spec-resizer").focus()
    page.keyboard.press("ArrowRight")
    expect(page.locator("#spec-resizer")).to_have_attribute("aria-valuenow", "38")
    assert page.locator(".spec-pane").bounding_box()["width"] > before
    before = page.locator(".input-group").bounding_box()["height"]
    page.locator("#data-resizer").focus()
    page.keyboard.press("ArrowDown")
    expect(page.locator("#data-resizer")).to_have_attribute("aria-valuenow", "52")
    assert page.locator(".input-group").bounding_box()["height"] > before
    handle = page.get_by_role("separator", name="Resize DM.ARM column", exact=True)
    handle.focus()
    page.keyboard.press("ArrowRight")
    expect(handle).to_have_attribute("aria-valuenow", "130")
    box = handle.bounding_box()
    page.mouse.move(box["x"] + 3, box["y"] + 5)
    page.mouse.down()
    page.mouse.move(box["x"] + 43, box["y"] + 5)
    page.mouse.up()
    expect(handle).to_have_attribute("aria-valuenow", "170")
    card = page.locator(f"#panel-i-{dm}")
    before = card.bounding_box()["width"]
    page.get_by_role("button", name="Widen DM input panel", exact=True).click()
    assert card.bounding_box()["width"] > before + 70
    page.get_by_role("button", name="Reset layout", exact=True).click()
    expect(page.locator("#spec-resizer")).to_have_attribute("aria-valuenow", "36")
    # Manual multiple input and output choices remain open while choosing datasets.
    page.locator("#input-picker summary").click()
    page.locator(f'[data-input-dataset="{ex}"]').check()
    expect(page.locator("#input-picker")).to_have_attribute("open", "")
    expect(page.locator(".input-group [data-panel]")).to_have_count(2)
    page.locator("#record-search").click()
    expect(page.locator("#input-picker")).not_to_have_attribute("open", "")
    page.locator("#output-picker summary").click()
    page.locator('[data-output-dataset="ADAE"][type=checkbox]').check()
    expect(page.locator(".output-group [data-panel]")).to_have_count(2)
    page.locator("#record-search").click()
    # Selecting an output in the comparison changes the specification and follows
    # ADSL-derived inputs all the way back to DM and EX, while displaying AE.
    other = page.locator("#panel-o-ADAE")
    other.locator('button[data-node="output.TRTSDT"]').click()
    expect(page.locator("#dataset-select")).to_have_value("ADAE")
    expect(page.locator('.input-group [data-domain="ADSL"]')).to_be_visible()
    expect(page.locator('.input-group [data-domain="DM"]')).to_be_visible()
    expect(page.locator('.input-group [data-domain="EX"]')).to_be_visible()
    expect(page.locator('.input-group [data-domain="AE"]')).to_be_visible()
    expect(
        page.locator(
            '.input-group [data-domain="EX"] th[data-node="table:' + ex + '.EXSTDTC"]'
        )
    ).to_have_count(1)
    visible = page.locator(
        '.input-group [data-domain="DM"] thead button[data-node]'
    ).all_text_contents()
    assert not any("AGE" in name for name in visible)
    assert page.locator('[data-line-node="spec.TRTSDT"].node-related').count() > 0
    expect(page.locator('#panel-o-ADAE th[data-node="output.TRTSDT"]')).to_have_class(
        "node-selected"
    )
    expect(page.locator('[data-line-node="spec.TRTSDT"]').first).to_be_in_viewport()
    capture(page, screenshots, "connected-datasets.png")
    # All columns can be restored; clearing focus restores manually pinned panels.
    page.locator("#column-mode").select_option("all")
    assert (
        page.locator('.input-group [data-domain="DM"] thead button[data-node]').count()
        > 10
    )
    page.get_by_role("button", name="Clear highlight", exact=True).click()
    expect(page.locator(".node-selected")).to_have_count(0)
    page.locator("#dataset-select").select_option("ADSL")
    page.locator('.input-group [data-domain="DM"] button[data-node="DM.ARM"]').click()
    expect(page.locator('#panel-o-ADSL th[data-node="output.TRT01P"]')).to_have_class(
        "node-related"
    )
    page.get_by_role("button", name="Clear highlight", exact=True).click()
    capture(page, screenshots, "dataset-workspace.png")
    # Restored links retain compared datasets and independently chosen table sizes.
    page.get_by_label("ADSL output rows per page", exact=True).select_option("50")
    bookmark = page.url
    page.reload()
    expect(page.get_by_label("ADSL output rows per page", exact=True)).to_have_value(
        "50"
    )
    expect(page.locator(".output-group [data-panel]")).to_have_count(2)
    shared = context.new_page()
    shared.goto(bookmark)
    expect(shared.get_by_label("ADSL output rows per page", exact=True)).to_have_value(
        "50"
    )
    shared.close()
    # Evidence and bottom-of-page comments retain the selected dataset context.
    page.locator("#dataset-select").select_option("ADAE")
    page.locator('.metric-strip [data-view="findings"]').click()
    expect(page.locator(".finding-card")).not_to_have_count(0)
    page.locator("#finding-search").fill("imputation")
    expect(page.locator(".finding-card")).to_have_count(1)
    page.locator(".finding-card summary").click()
    page.get_by_role("button", name="Open evidence in workspace", exact=True).click()
    expect(page.locator(".evidence-drawer")).to_be_visible()
    cited = page.get_by_role(
        "link", name="Open cited source", exact=True
    ).get_attribute("href")
    assert page.request.get(cited.split("#")[0]).status == 200
    capture(page, screenshots, "source-evidence.png")
    page.get_by_role("button", name="Close source evidence", exact=True).click()
    expect(page.locator("#comments-host script")).to_have_attribute(
        "data-term", "pilot7/studies/cdiscpilot01/ADAE"
    )
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.get_by_role("button", name="Copy review context", exact=True).click()
    expect(page.locator("#review-toast")).to_contain_text("copied")
    copied = page.evaluate("navigator.clipboard.readText()")
    assert "Dataset: ADAE\n" in copied and page.url in copied
    page.evaluate(
        'Object.defineProperty(navigator,"clipboard",{value:{writeText:async()=>{throw Error("Denied")}}})'
    )
    page.get_by_role("button", name="Copy review context", exact=True).click()
    expect(page.locator("#share-url")).to_have_value(copied)
    page.locator('.review-tabs [data-view="materials"]').click()
    for anchor in page.locator(".material-card a").all():
        href = anchor.get_attribute("href")
        if href.startswith(base):
            assert page.request.get(href).status == 200, href
    page.locator('.review-tabs [data-view="overview"]').click()
    expect(page.locator(".overview-table tbody tr")).to_have_count(10)
    expect(page.locator(".overview-table")).not_to_contain_text(
        "These are real results"
    )
    # Pilot and synthetic sections have separate galleries and dashboard purposes.
    page.get_by_role("link", name="All pilot studies", exact=True).click()
    expect(page.locator(".study-card")).to_have_count(
        len(
            json.loads((site_dir / "evidence/dashboard/index.json").read_text())[
                "studies"
            ]
        )
    )
    nav = page.locator(".md-nav--primary")
    expect(nav).to_contain_text("Pilot studies")
    expect(nav).to_contain_text("Synthetic data")
    page.locator('.study-card[href*="submission-pilot3"]').click()
    expect(page.locator("#output-table tbody tr")).to_have_count(3)
    page.locator("#dataset-select").select_option("ADADAS")
    p3 = json.loads(
        (site_dir / "evidence/dashboard/submission-pilot3/catalog.json").read_text()
    )
    d = next(d for d in p3["datasets"] if d["name"] == "ADADAS")
    aw = next(i["table"] for i in d["inputs"] if i["alias"] == "AW")
    page.locator("#input-picker summary").click()
    page.locator(f'[data-input-dataset="{aw}"]').check()
    page.locator("#record-search").click()
    expect(page.locator(f"#panel-i-{aw} tbody tr")).to_have_count(4)
    expect(page.locator(f"#panel-i-{aw} .pane-footer")).to_contain_text(
        "subject-independent lookup"
    )
    page.goto(base + "/synthetic/")
    synthetic_index = json.loads(
        (site_dir / "evidence/dashboard/synthetic/index.json").read_text()
    )
    expect(page.locator("#synthetic-dashboard .study-card")).to_have_count(
        len(synthetic_index["studies"])
    )
    page.locator('.study-card[href*="kn189"]').click()
    expect(page.locator(".synthetic-stage-grid article")).to_have_count(4)
    expect(page.locator("#synthetic-dashboard")).to_contain_text("ODM source inventory")
    expect(page.locator(".review-workbench")).to_have_count(0)
    expect(page.locator("#synthetic-dashboard")).to_contain_text("Not staged")
    expect(page.locator(".md-sidebar--primary")).to_be_visible()
    assert (
        page.get_by_role("link", name="Study source", exact=True)
        .get_attribute("href")
        .endswith("/kn189")
    )
    capture(page, screenshots, "synthetic-workspace.png")
    for width in [375, 768, 1600, 2560]:
        page.set_viewport_size({"width": width, "height": 1000})
        for view in ["datasets", "findings", "materials"]:
            page.goto(study + f"#cdiscpilot01/{view}/ADAE?focus=output.TRTSDT")
            if view == "datasets":
                expect(page.locator("#dataset-select")).to_be_visible()
            elif view == "findings":
                expect(
                    page.get_by_role("heading", name="Consistency verification report")
                ).to_be_visible()
            else:
                expect(page.locator(".material-card")).not_to_have_count(0)
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (
                width,
                view,
            )
            if width == 375 and view == "datasets":
                page.locator("#subject-summary").click()
                box = page.locator(".subject-popover").bounding_box()
                assert box["x"] >= 0 and box["x"] + box["width"] <= width
                page.locator("#record-search").click()
                capture(page, screenshots, "mobile-workspace.png")
        page.goto(base + "/studies/kn189/")
        expect(page.locator(".synthetic-stage-grid article")).to_have_count(4)
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (
            width,
            "synthetic",
        )
    page.goto(study + "#cdiscpilot01/datasets/ADAE?focus=output.TRTSDT")
    expect(page.locator("#panel-o-ADAE th.node-selected")).to_have_count(1)
    page.evaluate('document.body.dataset.mdColorScheme="slate"')
    capture(page, screenshots, "dark-workspace.png")
    page.goto(
        study
        + "#cdiscpilot01/datasets/UNKNOWN?subjects=UNKNOWN&outputs=UNKNOWN&rowSearch=%3Cimg%20src=x%3E"
    )
    expect(page.locator("#dataset-select")).to_have_value("ADSL")
    expect(page.locator("#output-table")).to_contain_text("No subjects selected")
    expect(page.locator("#record-search")).to_have_value("<img src=x>")
    expect(page.locator("#view-content img")).to_have_count(0)
    page.goto(study + "#cdiscpilot01/comments/ADAE")
    expect(page.locator("#input-table tbody tr")).not_to_have_count(0)
    expect(page.locator("#review-comments")).to_be_in_viewport()
    assert not errors, errors
    context.close()
    # A failure affects its own panel and remains retryable.
    failure_context = browser.new_context()
    failure_context.route(
        "https://giscus.app/client.js",
        lambda r: r.fulfill(body="", content_type="application/javascript"),
    )
    page = failure_context.new_page()
    attempts = []

    def once(route):
        if not attempts:
            attempts.append(True)
            route.fulfill(status=503, body="Unavailable")
        else:
            route.continue_()

    page.route("**/cdiscpilot01/tables/t000/0.json.gz", once)
    page.goto(study)
    expect(page.locator("#input-table .error-state")).to_be_visible()
    expect(page.locator("#output-table tbody tr")).to_have_count(3)
    page.locator("#input-table [data-retry]").click()
    expect(page.locator("#input-table tbody tr")).to_have_count(3)
    failure_context.close()
    decoded_context = browser.new_context()
    page = decoded_context.new_page()
    decoded_context.route(
        "https://giscus.app/client.js",
        lambda r: r.fulfill(body="", content_type="application/javascript"),
    )
    chunk = site_dir / "evidence/dashboard/cdiscpilot01/tables/t000/0.json.gz"
    page.route(
        "**/cdiscpilot01/tables/t000/0.json.gz",
        lambda r: r.fulfill(
            body=gzip.decompress(chunk.read_bytes()), content_type="application/json"
        ),
    )
    page.goto(study)
    expect(page.locator("#input-table tbody tr")).to_have_count(3)
    decoded_context.close()

    delayed = browser.new_context()
    delayed.route(
        "https://giscus.app/client.js",
        lambda r: r.fulfill(body="", content_type="application/javascript"),
    )
    page = delayed.new_page()
    pending = []
    page.route(
        "**/cdiscpilot01/tables/t000/1.json.gz", lambda route: pending.append(route)
    )
    page.goto(study)
    expect(page.locator("#output-table tbody tr")).to_have_count(3)
    page.locator("#subject-summary").click()
    page.get_by_role("button", name="Select all", exact=True).click()
    expect(page.locator("#input-table")).to_contain_text(
        "Loading selected study records"
    )
    page.locator("#record-search").fill(catalog["subjects"][0])
    expect(page.locator("#input-table")).to_contain_text(
        "Loading selected study records"
    )
    for route in pending:
        route.continue_()
    expect(page.locator("#input-table tbody tr")).to_have_count(1)
    delayed.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "site")
    parser.add_argument("--browser-path")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if not (args.site_dir / "evidence/dashboard/index.json").is_file():
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
            except Exception:
                if args.screenshots:
                    for n, context in enumerate(browser.contexts):
                        for m, page in enumerate(context.pages):
                            capture(page, args.screenshots, f"failure-{n}-{m}.png")
                raise
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    print(
        "Browser checks passed: separate pilot/synthetic dashboards, repository source links, 10/25/50/100 row counts, compared datasets, cross-specification lineage, dynamic columns, pane/column resizing, source evidence, shared URLs, inline comments, responsive layouts, and retryable panel errors. Comment posting/authentication is not exercised."
    )


if __name__ == "__main__":
    main()
