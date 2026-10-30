#!/usr/bin/env python3
"""Exercise the production two-source workspace with an explicitly synthetic fixture."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '.github/scripts'))
from test_dataset_define import DatasetDefineTests
from browser import check_dataset_define


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--browser-path')
    args.add_argument('--screenshots', type=Path)
    options = args.parse_args()
    fixture = DatasetDefineTests()
    fixture.setUp()
    try:
        site = fixture.root / 'site'
        destination = site / 'evidence/dashboard'
        destination.mkdir(parents=True)
        fixture.workspace(destination)
        (destination / 'index.json').write_text(json.dumps({'schema_version': 1, 'studies': [{'id': 'study'}], 'comments': {}}))
        shutil.copytree(ROOT / 'docs/assets', site / 'assets')
        shutil.copytree(ROOT / 'docs/stylesheets', site / 'stylesheets')
        page = site / 'studies/study/index.html'
        page.parent.mkdir(parents=True)
        page.write_text('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="../../stylesheets/dashboard.css">
<div id="study-dashboard" class="study-dashboard" data-study="study"></div>
<script type="module" src="../../assets/dashboard/app.js"></script>''')
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(site)))
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=options.browser_path)
                page = browser.new_page(viewport={'width': 1600, 'height': 1000})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                check_dataset_define(page, f'http://127.0.0.1:{server.server_port}/studies/study/#study/datasets/ADSL', options.screenshots)
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
    finally:
        fixture.doCleanups()
    print('Two-source fixture browser checks passed.')


if __name__ == '__main__':
    main()
