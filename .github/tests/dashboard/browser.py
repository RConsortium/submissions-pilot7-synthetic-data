#!/usr/bin/env python3
"""Exercise complete real-data review bundles in a browser, with no write actions."""

import argparse
import gzip
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
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


def assert_page_fits(page, selector):
    assert page.locator(selector).evaluate("""region => {
      const last = region.querySelector('tbody tr:last-child');
      return region.scrollHeight <= region.clientHeight + 1 &&
        last.getBoundingClientRect().bottom <= region.getBoundingClientRect().bottom + 1;
    }"""), selector + " clips the selected page of rows"


def displayed_source(page, specification):
    """The source document the specification pane shows."""
    view = page.locator("#spec-view").input_value()
    index = int(view.removeprefix("source:")) if view.startswith("source:") else 0
    return specification["documents"][index]


def assert_yaml_context(page, specification, inputs, intermediates):
    focus = displayed_source(page, specification)["lineage"]["focus"]
    for name, span in focus["inputs"].items():
        line = page.locator(f'#spec-L{span["start"]}')
        if name in inputs:
            expect(line).not_to_have_attribute("hidden", "")
        else:
            expect(line).to_have_attribute("hidden", "")
    span = focus["output_columns"]
    expect(page.locator(f'#spec-L{span["start"]}')).to_have_attribute("hidden", "")
    shown = page.locator('.spec-line[data-intermediate]:visible').evaluate_all(
        "lines => [...new Set(lines.map(line => line.dataset.intermediate))]"
    )
    assert set(shown) == set(intermediates), (shown, intermediates)


def check(browser, base, site_dir, screenshots):
    context = browser.new_context(viewport={"width": 1600, "height": 1000},
                                  permissions=["clipboard-read", "clipboard-write"])
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
    # Treatment codes use DM; exposure dates retain EX and its matching keys.
    for name in ["cdiscpilot01", "submission-pilot3", "submission-pilot5"]:
        url = base + f"/studies/{name}/#{name}/datasets/ADSL?focus=output."
        study_model = json.loads((site_dir / f"evidence/dashboard/{name}/catalog.json").read_text())
        dataset = next(d for d in study_model["datasets"] if d["name"] == "ADSL")
        spec = json.loads((site_dir / f'evidence/dashboard/{name}/{dataset["spec"]}').read_text())
        page.goto(url + "TRT01AN")
        expect(page.locator('.input-group [data-panel]')).to_have_count(1)
        expect(page.locator('.input-group [data-domain="DM"]')).to_be_visible()
        expect(page.locator('.input-group [data-domain="EX"]')).to_have_count(0)
        assert_yaml_context(page, spec, {"DM"}, set())
        expect(page.locator('[data-line-node="spec.TRT01A"]').first).not_to_be_visible()
        if name == "cdiscpilot01":
            capture(page, screenshots, "focused-treatment-specification.png")
        page.goto(url + "TRTSDT")
        expect(page.locator('.input-group [data-domain="EX"]')).to_be_visible()
        expect(page.locator('.input-group [data-domain="EX"] .key-badge')).not_to_have_count(0)
        assert_yaml_context(page, spec, {"DM", "EX"}, {"EX_FIRST"} if name == "submission-pilot3" else set())
        # The merged findings UI applies to every published pilot study.
        study_report = json.loads((site_dir / f"evidence/dashboard/{name}/report.json").read_text())
        issues = study_report["review"]["issues"]
        checks = study_report["review"]["counts"]["checks"]
        expect(page.locator(".consistency-summary")).to_contain_text(f"{len(issues)} findings awaiting review")
        expect(page.locator(".reference-summary")).to_contain_text("100% of reference datasets matched")
        expect(page.locator(".comparison-explanation")).to_contain_text("Findings can remain open even when reference agreement is 100%")
        critical = sum(i["critical"]["status"] == "yes" for i in issues)
        expect(page.locator(".consistency-summary .critical-counts")).to_contain_text(f"{critical} critical;")
        page.get_by_role("button", name="View consistency findings", exact=True).click()
        expect(page.locator(".result-count")).to_have_text(f"{len(issues)} of {len(issues)} issues \u00b7 {checks} supporting checks")
        expect(page.locator(".consistency-table tbody tr[data-finding-id]")).to_have_count(len(issues))
        expect(page.locator(".consistency-table thead th")).to_have_text([
            "Dataset / variable", "Impact / review", "Issue", "Critical finding", "Status", "Evidence"
        ])
        expect(page.locator("#issue-review")).to_have_count(0)
        for issue in issues:
            row = page.locator(f'[data-finding-id="{issue["id"]}"]')
            expect(row.locator(".issue-summary p")).to_have_text(issue["summary"])
        assert page.locator(".issue-summary").evaluate_all(
            "cells => cells.every(cell => getComputedStyle(cell).overflow === 'visible' "
            "&& getComputedStyle(cell).whiteSpace === 'normal')"
        )
        assert page.locator(".issue-impact").evaluate_all(
            "cells => cells.every(cell => getComputedStyle(cell).position === 'static')"
        )
        expect(page.get_by_role("columnheader", name="Status", exact=True)).to_be_visible()
        expect(page.locator(".consistency-table .issue-status .status")).to_have_text(
            ["Under Review"] * len(issues)
        )
        expect(page.locator(".consistency-table .finding-evidence")).to_have_count(0)
        expect(page.get_by_role("button", name="Copy review context", exact=True)).to_have_count(0)
        page.get_by_role("button", name="Define-XML comparison", exact=True).click()
        expect(page.locator('.define-comparison iframe')).to_have_count(2)
        expect(page.locator('.define-status')).to_contain_text(
            'Metadata matched' if study_model['validation']['define_xml']['comparison'] == 'matched' else 'Metadata differs')
        expect(page.locator('.define-differences tbody tr')).to_have_count(
            len(study_model['validation']['define_xml']['metadata']['differences']))
        expect(page.get_by_role('link', name='Download XML', exact=True)).to_have_count(2)
        for side, label in [('reference', 'Original'), ('candidate', 'yamaa-generated')]:
            frame = page.frame_locator(f'iframe[title="{label} XML source"]')
            expect(frame.locator('#L1')).to_be_visible()
            expect(page.locator(f'iframe[title="{label} XML source"]')).to_have_attribute(
                'src', base + f'/evidence/dashboard/{name}/define/{side}.html')
        assert '/define/ADSL' in page.url
        page.reload()
        expect(page.locator('.define-comparison iframe')).to_have_count(2)
        if name == 'cdiscpilot01':
            if screenshots:
                screenshots.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshots / 'define-xml-comparison.png'))
            page.set_viewport_size({'width': 600, 'height': 900})
            panes = page.locator('.define-pane').all()
            first, second = [pane.bounding_box() for pane in panes]
            assert second['y'] >= first['y'] + first['height']
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.set_viewport_size({'width': 1600, 'height': 1000})
    # A layered column opens the shared layer that writes its rule; its entry
    # keeps this package's historical metadata; the model resolves both.
    copied = json.loads((site_dir / "evidence/dashboard/cdiscpilot01/specs/adtte.json").read_text())
    page.goto(base + "/studies/cdiscpilot01/#cdiscpilot01/datasets/ADTTE?focus=output.AGE")
    expect(page.locator("#spec-caption")).to_contain_text("Focused view")
    paths = [document["path"] for document in copied["documents"]]
    defining = paths.index(copied["lineage"]["definitions"]["AGE"]["path"])
    assert defining > 0
    expect(page.locator("#spec-view")).to_have_value(f"source:{defining}")
    rule = "\n".join(page.locator(".spec-line.node-selected code").all_text_contents())
    assert "derivation: ADSL.AGE" in rule
    assert page.locator(".spec-omission:visible").count() > 0
    page.get_by_role("button", name="Copy source file", exact=True).click()
    expect(page.get_by_role("button", name="Copied", exact=True)).to_be_visible()
    assert page.evaluate("navigator.clipboard.readText()") == copied["documents"][defining]["text"]
    page.locator("#spec-view").select_option("source:0")
    selected = page.locator(".spec-line.node-selected code").all_text_contents()
    span = copied["lineage"]["spans"]["AGE"]
    authored = copied["text"].split("\n")[span["start"] - 1:span["end"]]
    assert selected == [line or " " for line in authored]
    assert "data_type: integer" in "\n".join(selected)
    page.locator("#spec-view").select_option("resolved")
    expect(page.locator("#spec-caption")).to_contain_text("model lines")
    expect(page.locator(".spec-pane .pane-footer")).to_contain_text("Engine-resolved model for inspection")
    assert "ADSL.AGE" in "\n".join(page.locator(".spec-line.node-selected code").all_text_contents())
    capture(page, screenshots, "resolved-copy-specification.png")
    page.reload()
    expect(page.locator("#spec-view")).to_have_value("resolved")
    page.locator("#spec-view").select_option("source:1")
    expect(page.get_by_role("link", name="Open source", exact=True)).to_have_attribute(
        "href", re.compile(re.escape(copied["documents"][1]["path"])))
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
    expect(page.locator("#input-picker summary")).to_have_text("Select domain (1)")
    expect(page.locator("#output-picker summary")).to_have_text("Select domain (1)")
    expect(page.locator('#input-table th[data-node="DM.STUDYID"]')).to_have_class("key-column")
    expect(page.locator('#output-table th[data-node="output.USUBJID"] .key-badge')).to_have_text("Key")
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
    assert_page_fits(page, "#input-table")
    assert_page_fits(page, "#output-table")
    ten_row_height = page.locator("#input-table").bounding_box()["height"]
    for size in [25, 50, 100]:
        page.get_by_label("DM input rows per page", exact=True).select_option(str(size))
        expect(page.locator("#input-table tbody tr")).to_have_count(size)
        page.get_by_label("ADSL output rows per page", exact=True).select_option(
            str(size)
        )
        expect(page.locator("#output-table tbody tr")).to_have_count(size)
        assert_page_fits(page, "#input-table")
        assert_page_fits(page, "#output-table")
        assert page.locator("#input-table").bounding_box()["height"] > ten_row_height
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
    assert_page_fits(page, "#input-table")
    assert_page_fits(page, "#output-table")
    assert page.locator("#input-table").bounding_box()["height"] < ten_row_height + 5
    # Specification, area split and table columns resize with keyboard and pointer.
    before = page.locator(".spec-pane").bounding_box()["width"]
    page.locator("#spec-resizer").focus()
    page.keyboard.press("ArrowRight")
    expect(page.locator("#spec-resizer")).to_have_attribute("aria-valuenow", "27")
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
    expect(page.locator("#spec-resizer")).to_have_attribute("aria-valuenow", "25")
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
    assert page.locator('[data-line-node="spec.TRTSDT"].node-selected').count() > 0
    assert page.locator('.spec-line[data-spec-kind="columns"][hidden]').count() > 0
    adae_spec = json.loads((site_dir / f'evidence/dashboard/cdiscpilot01/{next(d for d in catalog["datasets"] if d["name"] == "ADAE")["spec"]}').read_text())
    assert_yaml_context(page, adae_spec, {"AE", "ADSL"}, {"ADSL_SBJ"})
    expect(page.locator('#panel-o-ADAE th[data-node="output.TRTSDT"]')).to_have_class(
        "node-selected"
    )
    expect(page.locator('[data-line-node="spec.TRTSDT"]').first).to_be_in_viewport()
    expect(page.locator('#panel-o-ADAE th[data-node="output.AESEQ"] .key-badge')).to_have_text("Key")
    assert page.locator('#panel-o-ADAE th.key-column').first.evaluate("e=>getComputedStyle(e).backgroundColor") != page.locator('#panel-o-ADAE th.node-selected').evaluate("e=>getComputedStyle(e).backgroundColor")
    capture(page, screenshots, "connected-datasets.png")
    # All columns can be restored; clearing focus restores manually pinned panels.
    page.locator("#column-mode").select_option("all")
    expect(page.locator(".spec-line[hidden]")).to_have_count(0)
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
    cdisc_issues = json.loads(
        (site_dir / "evidence/dashboard/cdiscpilot01/report.json").read_text()
    )["review"]["issues"]
    cdisc_issue_count = len(cdisc_issues)
    expect(page.locator('.review-tabs [data-view="datasets"]')).to_have_text("SDTM -> ADaM")
    expect(page.locator('.review-tabs [data-view="overview"]')).to_have_text("Consistency findings")
    expect(page.locator('.consistency-summary .summary-value')).to_have_text(
        f"{cdisc_issue_count} findings awaiting review"
    )
    expect(page.locator('.consistency-summary [data-view="overview"]')).to_have_text("View consistency findings")
    page.locator('.review-tabs [data-view="overview"]').click()
    expect(page.locator(".consistency-table")).to_be_visible()
    expect(page.locator(".consistency-table tbody tr[data-finding-id]")).to_have_count(cdisc_issue_count)
    expect(page.locator("#view-content h2, #view-content .uncited")).to_have_count(0)
    page.locator("#finding-comparison").select_option("input_output")
    expect(page.locator(".consistency-table tbody")).to_contain_text("No issues match")
    expect(page.locator(".consistency-table tbody")).not_to_contain_text("Executed")
    page.locator("#finding-comparison").select_option("source_documents")
    page.locator("#finding-search").fill("imputation")
    expect(page.locator(".consistency-table tbody tr")).to_have_count(1)
    expect(page.locator(".consistency-table tbody")).to_contain_text("ADAE.ASTDT")
    expect(page.locator(".finding-evidence")).to_have_count(0)
    page.locator(".finding-trace > summary").click()
    expect(page.locator(".finding-evidence")).to_be_visible()
    expect(page.locator(".consistency-table tbody")).to_contain_text("No issue-specific data comparison")
    expect(page.locator('.finding-evidence a[href*="adae.yaml"]').first).to_have_attribute("href", re.compile(r"adae\.yaml#L\d+$"))
    capture(page, screenshots, "consistency-review.png")
    page.get_by_role("button", name="Open evidence in workspace", exact=True).click()
    expect(page.locator(".evidence-drawer")).to_be_visible()
    capture(page, screenshots, "source-evidence.png")
    page.locator(".evidence-drawer").get_by_role("button", name="View source", exact=True).first.click()
    expect(page.locator("#source-frame")).to_have_attribute(
        "src", re.compile(r"dataguide\.pdf#page=5$")
    )
    cited = page.locator("#source-frame").get_attribute("src")
    assert page.request.get(cited.split("#")[0]).body().startswith(b"%PDF")
    page.locator('.review-tabs [data-view="datasets"]').click()
    page.get_by_role("button", name="Close source evidence", exact=True).click()
    expect(page.locator("#comments-host script")).to_have_attribute(
        "data-term", "pilot7/studies/cdiscpilot01/ADAE"
    )
    expect(page.get_by_role("button", name="Copy review context", exact=True)).to_have_count(0)
    expect(page.locator("#share-fallback, #share-url")).to_have_count(0)
    page.locator('.review-tabs [data-view="materials"]').click()
    expect(page.locator("#view-content h2, #view-content h3")).to_have_count(0)
    primary_tabs = page.get_by_role("tablist", name="Document 1 files", exact=True)
    primary_tabs.get_by_role("tab", name="define-adam.xml", exact=True).click()
    expect(page.locator("#source-frame")).to_have_attribute("title", "Original XML HTML: define-adam.xml")
    expect(page.frame_locator("#source-frame").locator("table").first).to_be_visible()
    expect(page.locator("#document-select, #document-mode")).to_have_count(0)
    expect(page.get_by_role("link", name="Original document", exact=True)).to_have_count(0)
    expect(page.get_by_role("link", name="Published upstream source", exact=True)).to_have_count(0)
    expect(page.get_by_role("link", name="Source manifest", exact=True)).to_have_count(0)
    expect(page.locator(".source-viewer-heading")).not_to_contain_text("cdiscpilot01/spec/")
    expect(page.locator(".source-viewer-heading").get_by_role("link", name="Source", exact=True)).to_have_attribute("href", f'https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/{catalog["revision"]}/cdiscpilot01/spec/define/define-adam.xml')
    page.evaluate("window.originalSourceFrame=document.querySelector('#source-frame')")
    page.get_by_role("button", name="Compare side by side", exact=True).click()
    expect(page.locator(".source-pane")).to_have_count(2)
    secondary_tabs = page.get_by_role("tablist", name="Document 2 files", exact=True)
    expect(secondary_tabs.get_by_role("tab", name="define-adam.xml", exact=True)).to_be_disabled()
    secondary_tabs.get_by_role("tab", name="SAP.pdf", exact=True).click()
    expect(page.locator("#source-frame-compare")).to_have_attribute("src", re.compile(r"SAP\.pdf$"))
    assert page.evaluate("window.originalSourceFrame===document.querySelector('#source-frame')")
    left = page.locator(".source-pane").nth(0).bounding_box()
    right = page.locator(".source-pane").nth(1).bounding_box()
    assert left["x"] + left["width"] <= right["x"] and abs(left["y"] - right["y"]) < 2
    page.evaluate("window.comparedSourceFrame=document.querySelector('#source-frame-compare')")
    primary_tabs.get_by_role("tab", name="define-sdtm.xml", exact=True).click()
    assert page.evaluate("window.comparedSourceFrame===document.querySelector('#source-frame-compare')")
    primary_tabs.get_by_role("tab", name="define-adam.xml", exact=True).click()
    page.wait_for_load_state("networkidle")
    capture(page, screenshots, "source-documents-side-by-side.png")
    page.reload()
    expect(page.locator(".source-pane")).to_have_count(2)
    expect(page.locator("#source-frame-compare")).to_have_attribute("src", re.compile(r"SAP\.pdf$"))
    page.set_viewport_size({"width": 375, "height": 1000})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert page.locator(".source-pane").nth(1).bounding_box()["y"] > page.locator(".source-pane").nth(0).bounding_box()["y"]
    page.set_viewport_size({"width": 1600, "height": 1000})
    page.get_by_role("button", name="Close comparison", exact=True).click()
    expect(page.locator(".source-pane")).to_have_count(1)
    primary_tabs = page.get_by_role("tablist", name="Document 1 files", exact=True)
    primary_tabs.get_by_role("tab", name="define-adam.xml", exact=True).focus()
    page.keyboard.press("End")
    expect(primary_tabs.get_by_role("tab", name="dataguide.pdf", exact=True)).to_have_attribute("aria-selected", "true")
    page.keyboard.press("Home")
    expect(primary_tabs.get_by_role("tab", name="define-adam.xml", exact=True)).to_have_attribute("aria-selected", "true")
    expect(page.frame_locator("#source-frame").locator("table").first).to_be_visible()
    capture(page, screenshots, "original-xml.png")
    page.locator('.review-tabs [data-view="overview"]').click()
    page.get_by_role("button", name="Clear filters", exact=True).click()
    expect(page.locator(".consistency-table tbody tr")).not_to_have_count(0)
    page.locator("#finding-kind").select_option("inconsistent")
    expect(page.locator(".consistency-table tbody")).not_to_contain_text("Executed")
    page.locator("#finding-search").fill("no such source rule")
    expect(page.locator(".consistency-table tbody")).to_contain_text(
        "No issues match"
    )
    # Related checks form one issue; the primary trace is concise and its full
    # evidence remains available. Source links and impact subjects still work.
    page.get_by_role("button", name="Clear filters", exact=True).click()
    page.locator("#finding-comparison").select_option("documented_rules")
    page.locator("#finding-search").fill("HEIGHTBL*100")
    rule = page.locator(".consistency-table tbody tr.review-issue")
    expect(rule).to_have_count(1)
    expect(rule.locator("h3")).to_have_text("BMI formula uses the wrong height conversion")
    expect(rule.locator(".rule-id")).to_have_text("CR-5, CR-6")
    rule.locator(".finding-trace > summary").focus()
    page.keyboard.press("Enter")
    expect(rule).to_contain_text("253 / 254 records differ")
    expect(rule.locator(".quote-source + blockquote").first).to_contain_text("WEIGHTBL / ((HEIGHTBL*100)**2)")
    expect(rule.locator(".pattern-list").first).to_be_visible()
    expect(rule).to_contain_text("Agent review: agreed")
    rule.locator(".issue-citation").filter(has=page.locator("pre.spec-lines")).first.locator("summary").click()
    expect(rule.locator("pre.spec-lines mark").first).to_be_visible()
    capture(page, screenshots, "documented-rules.png")
    rule.get_by_role("button", name="View source", exact=True).first.click()
    expect(page.locator("#source-panel-0 iframe")).to_have_attribute(
        "src", re.compile(r"define-adam\.xml.*#ADSL\.BMIBL$")
    )
    page.locator('.review-tabs [data-view="overview"]').click()
    rule.locator(".finding-trace > summary").click()
    evidence = rule.get_by_role("button", name="Open evidence in workspace (253 subjects)", exact=True)
    evidence.click()
    expect(page.locator(".evidence-drawer")).to_be_visible()
    expect(page.locator("#subject-summary")).to_contain_text("253 /")
    page.get_by_role("button", name="Close source evidence", exact=True).click()
    page.locator('.review-tabs [data-view="overview"]').click()
    page.get_by_role("button", name="Clear filters", exact=True).click()
    page.locator("#finding-search").fill("BMIBLGR1")
    expect(rule).to_have_count(2)
    expect(rule.filter(has_text="Missing BMI is assigned")).to_contain_text("Alternative rule (BMIBLGR1__CODED_GE30) vs published reference: 1 subject differs")
    expect(rule.filter(has_text="Obese category code differs")).to_contain_text("Documented codelist vs published reference: 28 subjects differ")
    capture(page, screenshots, "bmi-issues.png")
    missing = rule.filter(has_text="Missing BMI is assigned")
    missing.locator(".finding-trace > summary").click()
    expect(missing.locator(".finding-evidence")).to_be_visible()
    capture(page, screenshots, "missing-bmi-trace.png")
    missing.get_by_role("button", name="Open evidence in workspace (1 subject)", exact=True).click()
    expect(page.locator("#subject-summary")).to_contain_text("1 /")
    expect(page.locator("#output-table tbody")).to_contain_text("01-702-1082")
    page.get_by_role("button", name="Close source evidence", exact=True).click()
    page.locator('.review-tabs [data-view="overview"]').click()
    page.get_by_role("button", name="Clear filters", exact=True).click()
    page.locator("#finding-search").fill("VISNUMEN")
    expect(rule).to_have_count(2)
    expect(rule.filter(has_text="Completion term is misspelled")).to_contain_text("No issue-specific data comparison")
    expect(rule.filter(has_text="Completion-only rule")).to_contain_text("Alternative rule (VISNUMEN__PROTOCOL_SPELLING) vs published reference: 144 subjects differ")
    capture(page, screenshots, "visit-issues.png")
    page.get_by_role("button", name="Clear filters", exact=True).click()
    for status in ("yes", "no", "needs_review"):
        page.locator("#finding-critical").select_option(status)
        expect(rule).to_have_count(sum(issue["critical"]["status"] == status for issue in cdisc_issues))
    page.locator("#finding-critical").select_option("yes")
    page.reload()
    expect(page.locator("#finding-critical")).to_have_value("yes")
    expect(rule).to_have_count(sum(issue["critical"]["status"] == "yes" for issue in cdisc_issues))
    page.get_by_role("button", name="Clear filters", exact=True).click()
    expect(page.locator("#finding-critical")).to_have_value("")
    expect(rule).to_have_count(len(cdisc_issues))
    # Pilot and synthetic reports share summary metrics and study tables.
    page.get_by_role("link", name="All pilot studies", exact=True).click()
    report = page.locator(".study-report")
    pilot_studies = [entry for entry in json.loads(
        (site_dir / "evidence/dashboard/index.json").read_text())["studies"]
        if entry.get("kind") != "synthetic"]
    expect(report.locator("#studies + .report-table thead a")).to_have_count(
        len(pilot_studies)
    )
    expect(report.locator("#dataset-results + .report-table thead a")).to_have_count(
        len(pilot_studies)
    )
    matrix = report.locator("#dataset-results + .report-table")
    expect(report).not_to_contain_text("CAR-T for ALL")
    for entry in pilot_studies:
        model = json.loads((site_dir / f"evidence/dashboard/{entry['id']}/catalog.json").read_text())
        if model["status"] == "pending":
            continue
        review = json.loads((site_dir / f"evidence/dashboard/{entry['id']}/report.json").read_text())["review"]
        for dataset in model["datasets"]:
            count = sum(i["dataset"] == dataset["name"] for i in review["issues"])
            label = f"{count} issue{'s' if count != 1 else ''}"
            badge = matrix.get_by_label(f"{label} for {model['title']} / {dataset['name']}", exact=True)
            expect(badge).to_have_text(label)
    expect(report.locator("#dataset-issues-note")).to_contain_text("Each issue counts once")
    expect(report.locator("details")).to_have_count(0)
    expect(report.locator(".report-provenance, #reading, #review-items")).to_have_count(0)
    expect(report).to_contain_text("Subject-Level Analysis Dataset")
    expect(report.locator(".reference-summary")).to_contain_text("100% of reference datasets matched")
    expect(report.locator(".consistency-summary")).to_contain_text("findings awaiting review")
    expect(report.locator(".comparison-explanation")).to_contain_text("Findings can remain open")
    expect(report.locator("#dataset-results + .report-table .report-status.good").first).to_have_text("Reference matched")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    nav = page.locator(".md-nav--primary")
    expect(nav).to_contain_text("Pilot studies")
    expect(nav).to_contain_text("Synthetic data")
    capture(page, screenshots, "study-report.png")
    page.goto(base + "/")
    home = page.locator(".pilot-metrics")
    expect(home).to_contain_text("Datasets matching reference")
    expect(home).to_contain_text("Cells in matching datasets")
    expect(home).to_contain_text("Consistency review")
    expect(home).to_contain_text("needing assessment")
    expect(home.locator("thead th")).to_have_text([
        "Study", "Published ADaM reference agreement", "Consistency review"
    ])
    assert home.evaluate("region => region.scrollWidth <= region.clientWidth + 1")
    capture(page, screenshots, "home-comparison-summary.png")
    page.set_viewport_size({"width": 375, "height": 1000})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert home.evaluate("region => region.scrollWidth <= region.clientWidth + 1")
    capture(page, screenshots, "home-comparison-phone.png")
    page.set_viewport_size({"width": 1600, "height": 1000})
    page.go_back()
    first_badge = matrix.locator("a.report-issues").first
    issue_count = int(first_badge.inner_text().split()[0])
    first_badge.click()
    expect(page.locator("#finding-search")).to_have_value("ADSL")
    expect(page.locator(".consistency-table tbody tr[data-finding-id]")).to_have_count(
        issue_count
    )
    page.go_back()
    # Instant navigation makes the report's relative links absolute.
    report.locator("#studies + .report-table").get_by_role("link", name="CDISC Pilot 01", exact=True).click()
    expect(page.locator('.review-tabs [data-view="datasets"]')).to_have_attribute(
        "aria-current", "page"
    )
    page.go_back()
    report.locator("#dataset-results + .report-table").get_by_role("link", name="Submission Pilot 3", exact=True).click()
    expect(page.locator("#output-table tbody tr")).to_have_count(3)
    page.locator('.review-tabs [data-view="materials"]').click()
    page.get_by_role("tablist", name="Document 1 files", exact=True).get_by_role("tab", name="adam-pilot-3.xlsx", exact=True).click()
    expect(page.locator("#source-frame")).to_have_attribute(
        "title", "Excel tables: adam-pilot-3.xlsx"
    )
    expect(page.frame_locator("#source-frame").locator("table").first).to_be_visible()
    expect(
        page.frame_locator("#source-frame").locator("#sheet-1-row-1")
    ).to_be_visible()
    capture(page, screenshots, "excel-source-tables.png")
    page.get_by_role("tablist", name="Document 1 files", exact=True).get_by_role("tab", name="define-adam.xml", exact=True).click()
    expect(page.frame_locator("#source-frame").locator("table").first).to_be_visible()
    page.locator('.review-tabs [data-view="datasets"]').click()
    page.locator("#dataset-select").select_option("ADADAS")
    expression = page.locator(
        '.spec-line[data-row-node="row.collected"][data-line-node="spec.ADT_RAW"]'
    ).first
    expression.click()
    expect(expression).to_have_class("spec-line node-selected")
    expect(expression).to_be_in_viewport()
    expect(
        page.locator(
            '.spec-line[data-spec-kind="columns"][data-line-node="spec.ADT_RAW"]'
        ).first
    ).to_have_class("spec-line node-selected")
    expect(
        page.locator(
            '.spec-line[data-row-node="row.collected"][data-line-node="spec.AVAL_RAW"]'
        ).first
    ).not_to_be_visible()
    page.locator(
        '.spec-line[data-row-node="row.collected"][data-line-node="row.collected"]'
    ).first.click()
    expect(
        page.locator('.spec-line[data-row-node="row.collected"]:not(.node-selected)')
    ).to_have_count(0)
    capture(page, screenshots, "focused-row-specification.png")
    page.get_by_role("button", name="Clear highlight", exact=True).click()
    expect(page.locator(".spec-line[hidden]")).to_have_count(0)
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
    synthetic = page.locator("#synthetic-dashboard.study-report")
    expect(synthetic.locator(".report-kpis > div")).to_have_count(5)
    expect(synthetic.get_by_role("table", name="Synthetic study overview").locator("thead th")).to_have_count(1 + len(synthetic_index["studies"]))
    expect(synthetic.get_by_role("table", name="Workflow readiness").locator("tbody tr")).to_have_count(4)
    expect(synthetic.locator(".report-provenance, #reading, .study-card")).to_have_count(0)
    capture(page, screenshots, "synthetic-report.png")
    expect(synthetic.get_by_role("link", name="CAR-T for ALL", exact=True)).to_be_visible()
    for name in ["kn189", "kn564"]:
        page.goto(base + f"/studies/{name}/#{name}/datasets/ADSL?focus=output.AGE")
        expect(page.locator(".review-hero h1")).to_have_text(name.upper())
        expect(page.locator(".review-workbench")).to_be_visible()
        expect(page.locator("#output-table tbody tr")).not_to_have_count(0)
        expect(page.locator('.input-group [data-domain="DM"]')).to_be_visible()
        expect(page.locator(".metric-strip")).to_contain_text("No independent published reference")
        expect(page.locator(".md-sidebar--primary")).not_to_be_visible()
        capture(page, screenshots, name + "-workspace.png")
        page.get_by_role("button", name="Analysis development", exact=True).click()
        expect(page.locator(".synthetic-development")).to_contain_text("Human analysis review pending")
        expect(page.get_by_role("link", name="Retained protocol and SAP", exact=True)).to_be_visible()
        capture(page, screenshots, name + "-development.png")
        page.get_by_role("link", name="All synthetic studies", exact=True).click()
        expect(page.locator("#synthetic-dashboard h1")).to_have_text("Synthetic data report")
    for width in [375, 768, 1600, 2560]:
        page.set_viewport_size({"width": width, "height": 1000})
        for view in ["datasets", "findings", "materials", "define"]:
            page.goto(study + f"#cdiscpilot01/{view}/ADAE?focus=output.TRTSDT")
            if view == "datasets":
                expect(page.locator("#dataset-select")).to_be_visible()
                expect(page.locator("#output-table tbody tr")).not_to_have_count(0)
                assert_page_fits(page, "#output-table")
            elif view == "findings":
                expect(page.get_by_role("region", name="Consistency findings", exact=True)).to_be_visible()
                page.locator(".finding-trace > summary").first.click()
                expect(page.locator(".finding-evidence").first).to_be_visible()
            elif view == "materials":
                expect(page.locator("#source-frame")).to_be_visible()
            else:
                expect(page.locator('.define-comparison iframe')).to_have_count(2)
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
        for path, title in [("synthetic", "Synthetic data report"), ("studies/kn189", "KN189"), ("studies/kn564", "KN564")]:
            page.goto(base + "/" + path + "/")
            expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
            if path == "synthetic":
                expect(page.get_by_role("table", name="Workflow readiness").locator("tbody tr")).to_have_count(4)
            else:
                expect(page.locator("#output-table tbody tr")).not_to_have_count(0)
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (width, path)
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
        "Browser checks passed: separate pilot/synthetic dashboards, repository source links, 10/25/50/100 row counts, compared datasets, cross-specification lineage, dynamic columns, pane/column resizing, source evidence, original-file tabs and two-pane comparisons, shared URLs, inline comments, responsive layouts, and retryable panel errors. Comment posting/authentication is not exercised."
    )


if __name__ == "__main__":
    main()
