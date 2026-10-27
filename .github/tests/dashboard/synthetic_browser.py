"""Exercise genuine synthetic build evidence and browser-local review drafts."""

import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from browser import PREFIX, PreviewHandler


def check_study(page, study, expected_findings, expected_datasets, screenshots=None):
    expect(page.locator('[data-finding-id]')).to_have_count(expected_findings)
    expect(page.get_by_role('table', name='Built synthetic datasets').locator('tbody tr')).to_have_count(expected_datasets)
    expect(page.locator('.synthetic-development')).to_contain_text('Human analysis review pending')
    search = page.locator('[data-findings-search]')
    search.fill('no-finding-can-match-this-value')
    expect(page.locator('[data-finding-id]:visible')).to_have_count(0)
    search.fill('')
    page.locator('[data-findings-kind]').select_option('gap')
    assert page.locator('[data-finding-id]:visible:not([data-kind="gap"])').count() == 0
    page.locator('[data-findings-kind]').select_option('all')
    finding = page.locator('[data-finding-id]').first
    identifier = finding.get_attribute('data-finding-id')
    finding.locator('summary').first.click()
    finding.locator('[data-review-choice]').select_option(index=1)
    finding.locator('[data-review-notes]').fill('AUTOMATED UI TEST - pending human review')
    expect(page.locator('[data-review-state]')).to_contain_text('saved in this browser')
    with page.expect_download() as download:
        page.locator('[data-review-export]').click()
    payload = json.loads(Path(download.value.path()).read_text())
    assert payload['study'] == study
    assert payload['state'] == 'human_review_draft_not_applied'
    assert payload['decisions'][identifier]['notes'] == 'AUTOMATED UI TEST - pending human review'
    page.reload()
    expect(page.locator(f'[data-review-notes="{identifier}"]')).to_have_value('AUTOMATED UI TEST - pending human review')
    if screenshots:
        screenshots.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshots / f'{study}-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'page overflows phone viewport'
    if screenshots:
        page.screenshot(path=str(screenshots / f'{study}-phone.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path, required=True)
    parser.add_argument('--offline-review', type=Path)
    parser.add_argument('--browser-path')
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(PreviewHandler, directory=str(args.site_dir.resolve())))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser_path)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            origin = f'http://127.0.0.1:{server.server_port}{PREFIX}'
            for study, findings, datasets in [('kn189', 17, 27), ('kn564', 19, 24)]:
                page.goto(origin + f'/studies/{study}/')
                check_study(page, study, findings, datasets, args.screenshots)
                href = page.locator('.synthetic-downloads a').first.get_attribute('href')
                assert href.startswith(origin + '/evidence/dashboard/synthetic/' + study)
                assert page.request.get(href).ok
                citation = page.locator('.synthetic-finding blockquote a').first.get_attribute('href')
                source = page.request.get(citation)
                assert source.ok and 'id="L' in source.text()
            assert not errors, errors
            context.close()
            if args.offline_review:
                # Managed browsers may prohibit file: navigation. Serve the exact
                # portable bytes locally and check that no external request occurs.
                portable = ThreadingHTTPServer(('127.0.0.1', 0), partial(
                    PreviewHandler, directory=str(args.offline_review.resolve().parent)))
                portable_worker = Thread(target=portable.serve_forever, daemon=True)
                portable_worker.start()
                try:
                    local_origin = f'http://127.0.0.1:{portable.server_port}{PREFIX}'
                    offline = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                    offline.on('pageerror', lambda error: errors.append(str(error)))
                    requests = []
                    offline.on('request', lambda request: requests.append(request.url))
                    offline.goto(local_origin + '/' + args.offline_review.name)
                    check_study(offline, 'kn189', 17, 27)
                    offline.locator('#study').select_option('kn564')
                    expect(offline.locator('[data-finding-id]')).to_have_count(19)
                    expect(offline.get_by_role('heading', name='KN564 study review')).to_be_visible()
                    assert not errors, errors
                    assert all(url.startswith((local_origin, 'data:')) for url in requests), requests
                    if args.screenshots:
                        offline.screenshot(path=str(args.screenshots / 'portable-kn564.png'))
                finally:
                    portable.shutdown()
                    portable.server_close()
                    portable_worker.join()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    print('Synthetic browser checks passed: both studies, measured findings, filters, retained citations, downloads, draft persistence/export, phone layout and portable review with no external requests.')


if __name__ == '__main__':
    main()
