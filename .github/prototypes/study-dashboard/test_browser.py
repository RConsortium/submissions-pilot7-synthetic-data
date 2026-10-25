#!/usr/bin/env python3
"""Exercise the built prototype in Chromium without production study evidence."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
PREFIX = '/review/project'


class PreviewHandler(SimpleHTTPRequestHandler):
    """Require a project prefix to catch broken root-relative navigation."""

    def do_GET(self):
        if not self.path.startswith(PREFIX + '/'):
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
        page.evaluate('document.activeElement.blur()')
        page.evaluate('window.scrollTo(0, 0)')
        page.wait_for_function('window.scrollY === 0')
        page.screenshot(path=str(directory / name), full_page=True,
                        animations='disabled')


def check(browser, base, screenshots):
    context = browser.new_context(viewport={'width': 1536, 'height': 1100})
    errors = []
    context.on('weberror', lambda error: errors.append(str(error.error)))
    page = context.new_page()
    study = base + '/studies/cdiscpilot01/'
    page.goto(study)
    expect(page.locator('#dataset-overview tbody tr')).to_have_count(10)
    expect(page.locator('.review-box')).to_contain_text('3 example questions')
    assert '${' not in page.locator('#study-dashboard').inner_text()
    assert page.locator('.dataset-desc').first.evaluate(
        'el => parseFloat(getComputedStyle(el).fontSize)') >= 13
    capture(page, screenshots, 'overview.png')

    page.get_by_label('Has doc questions').check()
    expect(page.locator('#dataset-overview tbody tr')).to_have_count(2)
    page.locator('#dataset-sort').select_option('rows')
    expect(page.locator('.dataset-code').first).to_contain_text('ADAE')
    page.get_by_label('Find a dataset').fill('subject')
    expect(page.locator('.dataset-code')).to_have_count(1)
    page.get_by_label('Find a dataset').fill('no such dataset')
    expect(page.locator('#dataset-overview')).to_contain_text('No datasets match')
    page.get_by_role('button', name='Clear filters', exact=True).click()
    expect(page.locator('#dataset-overview tbody tr')).to_have_count(10)

    page.get_by_role('button', name='2 open', exact=False).click()
    expect(page.locator('.finding-card')).to_have_count(2)
    expect(page.locator('#finding-dataset')).to_have_value('ADSL')
    page.get_by_label('Search documentation questions').fill('SAFFL')
    expect(page.locator('.finding-card')).to_have_count(1)
    page.locator('.finding-card summary').click()
    expect(page.locator('.finding-card details')).to_have_attribute('open', '')
    page.get_by_role('button', name='Explore ADSL.SAFFL').click()
    expect(page.locator('#column-select')).to_have_value('SAFFL')
    expect(page.locator('#spec-panel')).to_be_visible()
    expect(page.locator('.comparison-tables th')).to_have_count(4)
    expect(page.locator('.preview-panel').first.locator('th')).to_have_count(5)
    page.get_by_label('Search sample rows').fill('72')
    expect(page.locator('.preview-table tbody tr')).to_have_count(3)
    expect(page.locator('.preview-table tbody tr').first).to_contain_text('DEMO-002')
    page.get_by_label('Highlight subject', exact=True).select_option('DEMO-002')
    expect(page.locator('tr.highlighted')).to_have_count(3)
    bookmark = page.url
    page.reload()
    expect(page.locator('#row-search')).to_have_value('72')
    expect(page.locator('#column-select')).to_have_value('SAFFL')
    expect(page.locator('tr.highlighted')).to_have_count(3)
    expect(page.locator('#spec-panel')).to_be_visible()
    shared = context.new_page()
    shared.goto(bookmark)
    expect(shared.locator('tr.highlighted')).to_have_count(3)
    expect(shared.locator('#row-search')).to_have_value('72')
    shared.close()

    with page.expect_download() as download:
        page.get_by_role('button', name='Sample CSV', exact=True).click()
    assert 'illustrative-preview.csv' in download.value.suggested_filename
    csv = Path(download.value.path()).read_text()
    assert csv.splitlines() == ['"USUBJID","SAFFL"', '"DEMO-002","Y"']

    context.grant_permissions(['clipboard-read', 'clipboard-write'])
    page.get_by_role('button', name='Copy view link').click()
    expect(page.locator('#toast')).to_contain_text('Link copied')
    assert page.evaluate('navigator.clipboard.readText()') == bookmark

    # Clipboard denial must leave a usable, selected text field.
    page.evaluate('Object.defineProperty(navigator, "clipboard", '
                  '{value: {writeText: async () => {throw Error("Denied")}}})')
    page.get_by_role('button', name='Copy view link').click()
    expect(page.locator('#share-url')).to_be_visible()
    expect(page.locator('#share-url')).to_have_value(bookmark)
    page.get_by_role('button', name='Reset preview').click()
    expect(page.locator('.preview-table tbody tr')).to_have_count(9)
    expect(page.locator('tr.highlighted')).to_have_count(0)
    page.get_by_label('Search sample rows').fill('not present')
    expect(page.locator('.preview-panel').first).to_contain_text('No sample rows match')
    page.get_by_role('button', name='Reset preview').click()
    page.get_by_label('Find a dataset').fill('events')
    expect(page.locator('.dataset-option')).to_have_count(1)
    page.locator('.dataset-option').click()
    expect(page.locator('.detail-header h3')).to_contain_text('ADAE')
    page.get_by_role('button', name='Clear filters', exact=True).click()
    page.get_by_role('button', name='Hide specification').click()
    page.get_by_label('Highlight subject', exact=True).select_option('DEMO-002')
    capture(page, screenshots, 'dataset-workspace.png')

    page.get_by_role('button', name='Documentation review', exact=False).first.click()
    expect(page.locator('#view-content h2')).to_be_focused()
    page.get_by_role('button', name='Clear filters', exact=True).click()
    expect(page.locator('.finding-card')).to_have_count(3)
    capture(page, screenshots, 'documentation-findings.png')
    page.get_by_label('Search documentation questions').fill('absent')
    expect(page.locator('#finding-results')).to_contain_text('No matching questions')
    page.get_by_label('Search documentation questions').fill('<img src=x onerror=alert(1)>')
    page.reload()
    expect(page.locator('#finding-search')).to_have_value('<img src=x onerror=alert(1)>')
    expect(page.locator('#finding-results img')).to_have_count(0)

    # Invalid incoming state falls back to available study data.
    page.goto(study + '#cdiscpilot01/datasets/UNKNOWN?column=UNKNOWN&subject=UNKNOWN&sort=UNKNOWN')
    expect(page.locator('.detail-header h3')).to_contain_text('ADSL')
    expect(page.locator('#column-select')).to_have_value('')
    expect(page.locator('#subject-select')).to_have_value('')
    page.get_by_role('button', name='Evidence', exact=True).click()
    with page.expect_download() as download:
        page.get_by_role('button', name='Sample evidence', exact=True).click()
    assert '"illustrative": true' in Path(download.value.path()).read_text()
    page.go_back()
    expect(page.locator('#row-search')).to_be_visible()
    page.go_forward()
    expect(page.get_by_role('button', name='Sample evidence', exact=True)).to_be_visible()

    # Material instant navigation reuses listeners and resets study state.
    page.locator('.md-nav--primary a[href*="submission-pilot3"]').click()
    expect(page.locator('#study-dashboard')).to_have_attribute('data-study', 'submission-pilot3')
    expect(page.locator('#dataset-overview tbody tr')).to_have_count(5)
    page.get_by_label('Find a dataset').fill('events')
    expect(page.locator('.dataset-code')).to_have_count(1)
    assert PREFIX + '/studies/' in page.url
    page.goto(base + '/#submission-pilot5/datasets/ADAE')
    expect(page.locator('#study-dashboard')).to_have_attribute('data-study', 'submission-pilot5')
    expect(page.locator('.detail-header h3')).to_contain_text('ADAE')
    assert PREFIX + '/studies/submission-pilot5/' in page.url

    page.goto(base + '/studies/submission-pilot6/')
    expect(page.locator('.findings-stat')).to_contain_text('Not reviewed')
    page.get_by_role('button', name='Documentation review', exact=False).first.click()
    expect(page.locator('#view-content')).to_contain_text('Documentation review not yet run')
    expect(page.locator('.finding-card')).to_have_count(0)
    page.goto(base + '/studies/')
    page.get_by_role('button', name='Submission Pilot 3', exact=False).click()
    expect(page.locator('#study-dashboard')).to_have_attribute('data-study', 'submission-pilot3')
    assert PREFIX + '/studies/submission-pilot3/' in page.url

    for width in (375, 768, 1536):
        page.set_viewport_size({'width': width, 'height': 900})
        for view in ('overview', 'datasets', 'findings'):
            page.goto(study + '#cdiscpilot01/' + view + '/ADAE')
            expect(page.locator('#view-content h2').first).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, view)
            if width == 375 and view == 'datasets':
                capture(page, screenshots, 'mobile-workspace.png')
    page.goto(study + '#cdiscpilot01/datasets/ADAE?subject=DEMO-002')
    page.evaluate('document.body.dataset.mdColorScheme="slate"')
    expect(page.locator('tr.highlighted')).to_have_count(3)
    capture(page, screenshots, 'dark-workspace.png')
    assert not errors, errors
    context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path,
                        default=ROOT / '.build/study-dashboard-preview/site')
    parser.add_argument('--browser-path')
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    if not args.site_dir.joinpath('index.html').is_file():
        parser.error('Build the prototype before running browser checks.')
    handler = partial(PreviewHandler, directory=str(args.site_dir.resolve()))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser_path)
            try:
                check(browser, f'http://127.0.0.1:{server.server_port}{PREFIX}', args.screenshots)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    print('Browser checks passed: filters, review links, URL state, exports, '
          'instant navigation, project prefix, pending states, mobile, and dark mode.')


if __name__ == '__main__':
    main()
