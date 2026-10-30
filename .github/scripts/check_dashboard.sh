#!/usr/bin/env bash
set -euo pipefail
python -m unittest discover -s .github/tests/dashboard -p 'test_*.py' -v
node --test .github/tests/dashboard/*.test.js
python .github/tests/dashboard/review_sources_browser.py
python .github/tests/dashboard/dataset_define_browser.py
python .github/tests/dashboard/browser.py --site-dir "${1:-site}" --screenshots .build/dashboard-browser
python .github/tests/dashboard/synthetic_browser.py --site-dir "${1:-site}"
