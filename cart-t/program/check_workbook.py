#!/usr/bin/env python3
"""Browser regression checks for the generated statistical review workbook.

Install .github/tests/dashboard/requirements.txt for Playwright. Use an
installed Chromium/Chrome or Playwright's installed Chromium. The temporary
preview listens on loopback only; it does not publish a website.
"""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
from threading import Thread

from playwright.sync_api import sync_playwright

STUDY = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def check(page, screenshots=None):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.wait_for_selector("#data-table tbody tr", timeout=30000)
    assert page.locator("#data-table tbody tr").count() == 100
    page.locator("#search").fill("DF-001")
    assert page.locator("#data-table tbody tr").count() == 1
    page.locator("#data-table tbody tr").first.click()
    assert "DF-001" in page.locator("#detail-title").inner_text()
    assert page.locator("#detail details").count() > 0
    page.get_by_role("button", name="AGE", exact=True).click()
    assert "DM.AGE" in page.locator("#detail").inner_text()
    page.locator("#dataset").select_option("ADLB")
    page.locator("#search").fill("DF-001")
    assert page.locator("#data-table tbody tr").count() > 0
    page.locator("#data-table tbody tr").first.click()
    assert "Linked LB record" in page.locator("#detail").inner_text()
    assert "Original CRF items" in page.locator("#detail").inner_text()
    page.locator("#dataset").select_option("ADQS")
    assert page.locator("#detail-title").inner_text() == "Source and derivation"
    page.locator("#search").fill("SF12PF")
    assert page.locator("#data-table tbody tr").count() > 0
    page.locator("#search").fill("")
    page.locator("#next").click()
    assert "page 2" in page.locator("#count").inner_text()
    page.get_by_role("button", name="Derivations", exact=True).click()
    assert "domain: ADQS" in page.locator("#yaml").inner_text()
    page.get_by_role("button", name="Review queries", exact=True).click()
    assert "DM.COUNTRY" in page.locator("#issues").inner_text()
    page.get_by_role("button", name="Verification and archive", exact=True).click()
    assert "PASS - xml_items_preserved" in page.locator("#checks").inner_text()
    page.get_by_role("button", name="Records and source", exact=True).click()
    if screenshots:
        screenshots.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshots / "desktop.png"))
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    if screenshots:
        page.screenshot(path=str(screenshots / "mobile.png"))
    links = page.evaluate("Object.values(datasets).flatMap(d=>[d.csv,d.xpt])")
    assert all((STUDY / "tlf" / link).resolve().is_file() for link in links)
    assert not errors, errors
    return {"status": "passed", "javascript_errors": errors,
            "coverage": ["subject search", "pagination", "source items", "variable derivations",
                         "SDTM links", "subscales", "queries", "audit", "download links", "mobile width"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", help="Optional browser executable")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(STUDY)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            executable = args.chromium or shutil.which("chromium") or shutil.which("google-chrome")
            options = {"executable_path": executable} if executable else {}
            browser = playwright.chromium.launch(headless=True, **options)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"http://127.0.0.1:{server.server_port}/tlf/review.html", timeout=90000)
            print(json.dumps(check(page, args.screenshots), indent=2))
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
